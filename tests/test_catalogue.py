"""Run with python -m unittest discover -s tests -p test_catalogue.py -v."""
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from tool import factory, subscriptions as s


class CatalogueChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patcher = patch.object(factory, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.snapshot = {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
            'providers': [{'cli': 'codex', 'installed': True, 'models': [
                {'id': 'gpt-6-luna', 'supported_efforts': ['low']},
                {'id': 'gpt-6.1-sol', 'supported_efforts': ['high']}],
                'auth': 'SUBSCRIPTION_LOGIN', 'access': 'METADATA_VERIFIED',
                'billing': 'SUBSCRIPTION_ONLY_REQUIRED',
                'quota_groups': [{'name': 'Codex Models', 'buckets': [{'remaining_fraction': .8}]}]}]}

    def test_scan_once_reuse_refresh_account_only_then_explicit_rescan(self):
        with patch.object(s, 'inventory', return_value=self.snapshot) as scan, \
             patch.object(s, 'refresh_accounts', side_effect=lambda data, *a: data) as live:
            first, _ = factory.startup_inventory()
            cache = (self.root / '.factory/model-catalogue.json').read_bytes()
            second, _ = factory.startup_inventory()
            self.assertEqual(first['providers'], second['providers'])
            self.assertEqual((self.root / '.factory/model-catalogue.json').read_bytes(), cache)
            self.assertEqual(scan.call_count, 1)
            self.assertEqual(live.call_count, 1)
            factory.startup_inventory(refresh=True)
            self.assertEqual(scan.call_count, 2)

    def test_corrupt_cache_never_silently_rescans(self):
        cache = self.root / '.factory/model-catalogue.json'
        cache.parent.mkdir()
        for value in ('broken', 'null', '{"schema_version":1,"providers":[{}]}'):
            cache.write_text(value)
            with patch.object(s, 'inventory') as scan:
                with self.assertRaisesRegex(ValueError, 'providers --scan'):
                    factory.startup_inventory()
                scan.assert_not_called()

    def test_refresh_keeps_pool_blocks_outage_and_recovers_without_model_listing(self):
        before = copy.deepcopy(self.snapshot)
        live = {'access': 'METADATA_VERIFIED', 'quota_groups': before['providers'][0]['quota_groups']}
        def auth(*a, **k): return {'exit_code': 0, 'stdout': 'ChatGPT', 'stderr': ''}
        with patch.object(s, 'codex_metadata', return_value=live) as metadata:
            fresh = s.refresh_accounts(before, auth, lambda name: name, {})
            metadata.assert_called_once_with(unittest.mock.ANY, {}, include_models=False)
        self.assertEqual(before, self.snapshot)
        self.assertEqual(fresh['providers'][0]['models'], before['providers'][0]['models'])
        self.assertEqual(s.route(fresh, 'SIMPLE')['selected']['model'], 'gpt-6-luna')
        self.assertEqual(s.route(fresh, 'COMPLEX')['selected']['model'], 'gpt-6.1-sol')
        with patch.object(s, 'codex_metadata', return_value={'access': 'NOT_PROBED', 'quota_groups': []}):
            outage = s.refresh_accounts(before, auth, lambda name: name, {})
        self.assertEqual(s.route(outage, 'SIMPLE')['status'], 'BLOCKED')
        with patch.object(s, 'codex_metadata', return_value=live):
            recovered = s.refresh_accounts(outage, auth, lambda name: name, {})
        self.assertIsNotNone(s.route(recovered, 'SIMPLE')['selected'])

    def test_quota_only_rpc_never_requests_model_list_and_scan_retains_models_on_quota_failure(self):
        for include_models in (False, True):
            frames = [{'id': 1, 'result': {}}]
            if include_models:
                frames.append({'id': 2, 'result': {'data': [{'id': 'gpt-6-luna',
                    'supportedReasoningEfforts': [{'reasoningEffort': 'low'}]}], 'nextCursor': None}})
            frames.append({'id': 20, 'error': {'code': -1}})
            stream = io.StringIO()
            proc = MagicMock(stdin=stream, stdout=io.StringIO('\n'.join(json.dumps(f) for f in frames)+'\n'))
            tree = MagicMock()
            tree.spawn.return_value = proc
            # Keep stdin observable after the native cleanup closes it.
            proc.stdin = MagicMock()
            with patch('tool.sessions.ProcessTree', return_value=tree):
                result = s.codex_metadata(lambda name: name, {}, include_models=include_models)
            sent = ''.join(call.args[0] for call in proc.stdin.write.call_args_list)
            self.assertEqual('model/list' in sent, include_models)
            self.assertEqual(result['access'], 'NOT_PROBED')
            self.assertEqual(bool(result['models']), include_models)


if __name__ == '__main__':
    unittest.main()
