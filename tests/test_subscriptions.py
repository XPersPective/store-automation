import copy
from datetime import datetime, timedelta, timezone
import json
import io
import unittest
from unittest.mock import MagicMock, patch

from tool import subscriptions as s


class SubscriptionChecks(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.groups = [{'name': name, 'buckets': [
            {'id': name + '-5h', 'window': '5h', 'remaining_fraction': left},
            {'id': name + '-weekly', 'window': 'weekly', 'remaining_fraction': left}]
        } for name, left in [('Gemini Models', .8), ('Claude and GPT models', 1)]]
        self.snapshot = {'captured_at': self.now.isoformat(), 'excluded': ['qwen'], 'providers': [
            {'cli': 'agy', 'access': 'METADATA_VERIFIED', 'billing': 'NO_CREDITS_AVAILABLE',
             'models': [{'id': name} for name in ('gemini-3.8-flash-low', 'gemini-3.8-flash-medium',
                        'gemini-3.1-pro-high', 'claude-sonnet-5-5-low', 'claude-opus-5-5-high')],
             'quota_groups': self.groups}]}

    def test_risk_floor_and_effort_are_separate_from_abundant_quota(self):
        self.assertEqual(s.route(self.snapshot, 'SIMPLE')['selected']['model'], 'gemini-3.8-flash-low')
        self.assertEqual(s.route(self.snapshot, 'STANDARD')['selected']['effort'], 'medium')
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['selected']['model'], 'gemini-3.1-pro-high')

    def test_fresh_codex_equivalent_route_survives_agy_shared_exhaustion(self):
        self.snapshot['providers'].append({'cli': 'codex', 'auth': 'SUBSCRIPTION_LOGIN',
            'access': 'METADATA_VERIFIED', 'billing': 'SUBSCRIPTION_ONLY_REQUIRED',
            'models': [{'id': name, 'supported_efforts': ['low', 'medium', 'high']}
                       for name in s.CODEX_TIERS],
            'quota_groups': [{'name': 'Codex Models', 'buckets': [{'remaining_fraction': .62}, {'remaining_fraction': .53}]}]})
        self.groups[0]['buckets'][0]['remaining_fraction'] = .1
        self.snapshot['excluded_model_prefixes'] = ['claude-']
        selected = s.route(self.snapshot, 'COMPLEX')['selected']
        self.assertEqual((selected['provider'], selected['model'], selected['effort']),
                         ('codex', 'gpt-5.6-sol', 'high'))
        self.assertEqual(s.route(self.snapshot, 'SIMPLE')['selected']['model'], 'gpt-5.6-luna')
        self.assertEqual(s.route(self.snapshot, 'STANDARD')['selected']['model'], 'gpt-5.6-terra')
        provider = self.snapshot['providers'][1]
        for field, value in (('auth', 'UNKNOWN'), ('access', 'NOT_PROBED'), ('billing', 'PAID_API')):
            old = provider[field]
            provider[field] = value
            self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')
            provider[field] = old
        provider['quota_groups'][0]['buckets'][0]['remaining_fraction'] = None
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')
        provider['quota_groups'][0]['buckets'][0]['remaining_fraction'] = .8
        provider['models'] = [{'id': 'gpt-999-sol', 'supported_efforts': ['high']}]
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')

    def test_codex_metadata_rpc_is_sanitized_bounded_and_owned(self):
        model = {'id': 'gpt-5.6-luna', 'supportedReasoningEfforts': [{'reasoningEffort': 'low'}],
                 'private': 'synthetic-secret'}
        quota = {'rateLimitsByLimitId': {'codex': {'primary': {'usedPercent': 47},
                   'secondary': {'usedPercent': 38}}}, 'accountId': 'synthetic-account'}
        frames = [{'id': 1, 'result': {}}, {'id': 2, 'result': {'data': [model], 'nextCursor': None}},
                  {'id': 20, 'result': quota}]
        proc = MagicMock(stdin=io.StringIO(), stdout=io.StringIO('\n'.join(json.dumps(frame) for frame in frames)+'\n'))
        tree = MagicMock()
        tree.spawn.return_value = proc
        with patch('tool.sessions.ProcessTree', return_value=tree):
            result = s.codex_metadata(lambda cli: cli, {'safe': 'env'})
        tree.close.assert_called_once_with()
        self.assertIn('forced_login_method="chatgpt"', tree.spawn.call_args.args[0])
        self.assertEqual(result['access'], 'METADATA_VERIFIED')
        self.assertEqual(result['models'], [{'id': 'gpt-5.6-luna', 'supported_efforts': ['low'], 'access': 'CATALOGUE_ONLY'}])
        self.assertEqual([window['remaining_fraction'] for window in result['quota_groups'][0]['buckets']], [.53, .62])
        self.assertNotIn('synthetic', json.dumps(result))

    def test_codex_metadata_malformed_or_process_failure_never_authorizes_access(self):
        failures = [[], [{'id': 1, 'error': {'code': -1}}],
                    [{'id': 1, 'result': {}}, {'id': 2, 'result': {'data': [{}]}}],
                    [{'id': 1, 'result': {}}, {'id': 2, 'result': {'data': [], 'nextCursor': None}},
                     {'id': 20, 'result': {'rateLimits': {'primary': {'usedPercent': None}, 'secondary': {}}}}],
                    [{'id': 1, 'result': {}}] + [{'id': page + 2, 'result': {'data': [], 'nextCursor': 'more'}} for page in range(10)]]
        for frames in failures:
            proc = MagicMock(stdin=io.StringIO(), stdout=io.StringIO('\n'.join(json.dumps(frame) for frame in frames)+'\n'))
            tree = MagicMock()
            tree.spawn.return_value = proc
            with patch('tool.sessions.ProcessTree', return_value=tree):
                result = s.codex_metadata(lambda cli: cli, {}, timeout=.2)
            self.assertEqual(result['access'], 'NOT_PROBED')
            self.assertEqual(result['models'], [])
            tree.close.assert_called_once_with()
        tree = MagicMock()
        tree.spawn.side_effect = OSError('process unavailable')
        with patch('tool.sessions.ProcessTree', return_value=tree):
            self.assertEqual(s.codex_metadata(lambda cli: cli, {})['access'], 'NOT_PROBED')
        tree.close.assert_called_once_with()

    def test_public_report_requires_identity_types_and_authoritative_usage(self):
        report = {'task': 'PB-123', 'role': 'Reviewer', 'provider': 'codex', 'model': 'gpt-5.6-luna',
                  'effort': 'low', 'state': 'BLOCKED', 'changed_files': [], 'evidence': ['observed check'],
                  'usage': {'input_tokens': 0, 'output_tokens': None}, 'blockers': ['missing access'], 'next_action': 'wait'}
        self.assertTrue(s.report_valid(report, 'PB-123'))
        self.assertFalse(s.report_valid(report, 'PB-124'))
        for field in s.REPORT_FIELDS:
            bad = dict(report)
            del bad[field]
            self.assertFalse(s.report_valid(bad))
        for usage in ([], {'input_tokens': True}, {'input_tokens': -1}, {'input_tokens': float('inf')}, {'input_tokens': '5'}):
            self.assertFalse(s.report_valid(dict(report, usage=usage)))
        self.assertTrue(s.report_valid(dict(report, usage=None)))

    def test_shared_bucket_reserve_excludes_all_gemini_siblings(self):
        self.groups[0]['buckets'][1]['remaining_fraction'] = .10
        result = s.route(self.snapshot, 'COMPLEX')
        self.assertEqual(result['selected']['model'], 'claude-opus-5-5-high')
        self.assertTrue(all(c['quota_group'] != 'Gemini Models' for c in result['candidates']))
        self.groups[1]['buckets'][0]['remaining_fraction'] = 0
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')

    def test_reserve_requires_saved_handoff_and_never_replaces_coordinator(self):
        for actor in ('coordinator', 'worker'):
            self.assertEqual(s.reserve_decision(actor, .11), 'READY')
            self.assertEqual(s.reserve_decision(actor, .10), 'CHECKPOINT_REQUIRED')
            self.assertEqual(s.reserve_decision(actor, .10, equivalent_verified=True), 'CHECKPOINT_REQUIRED')
            self.assertEqual(s.reserve_decision(actor, .10, handoff_saved=True), 'WAIT_FOR_RESET')
            for unknown in (None, True, -1, 2, float('nan')):
                self.assertEqual(s.reserve_decision(actor, unknown, True, True), 'QUOTA_UNKNOWN')
        self.assertEqual(s.reserve_decision('coordinator', 0, True, True), 'WAIT_FOR_RESET')
        self.assertEqual(s.reserve_decision('worker', 0, True, True), 'REROUTE_APPROVED')
        for args in (('director', .1), ('worker', .1, 'yes'), ('worker', .1, True, 'yes')):
            with self.assertRaises(ValueError):
                s.reserve_decision(*args)

    def test_unknown_or_nonfinite_quota_is_never_available(self):
        for invalid in (None, True, -1, 2, float('inf'), float('nan')):
            with self.subTest(value=invalid):
                snapshot = copy.deepcopy(self.snapshot)
                for group in snapshot['providers'][0]['quota_groups']:
                    group['buckets'][0]['remaining_fraction'] = invalid
                self.assertIsNone(s.route(snapshot, 'SIMPLE')['selected'])

    def test_excluded_provider_overage_or_unmapped_model_is_blocked(self):
        self.snapshot['excluded_model_prefixes'] = ['claude-']
        self.groups[0]['buckets'][0]['remaining_fraction'] = 0
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')
        self.snapshot['excluded_model_prefixes'] = []
        self.groups[0]['buckets'][0]['remaining_fraction'] = .8
        self.snapshot['excluded'].append('agy')
        self.assertEqual(s.route(self.snapshot, 'SIMPLE')['status'], 'BLOCKED')
        self.snapshot['excluded'] = []
        self.snapshot['providers'][0]['billing'] = 'OVERAGE_POLICY_REQUIRED'
        self.assertEqual(s.route(self.snapshot, 'SIMPLE')['status'], 'BLOCKED')
        self.snapshot['providers'][0]['billing'] = 'NO_CREDITS_AVAILABLE'
        self.snapshot['providers'][0]['models'] = [{'id': 'unknown-strong-high'}]
        self.assertEqual(s.route(self.snapshot, 'SPECIALIZED')['status'], 'BLOCKED')

    def test_stale_future_or_naive_inventory_requires_refresh(self):
        for value in (self.now - timedelta(seconds=301), self.now + timedelta(seconds=10), self.now.replace(tzinfo=None)):
            self.snapshot['captured_at'] = value.isoformat()
            with self.assertRaises(ValueError):
                s.route(self.snapshot, 'SIMPLE', now=self.now)

    def test_metadata_scan_does_not_publish_auth_identity_or_infer_login(self):
        def run(argv, **kwargs):
            data = {'loggedIn': True, 'authMethod': 'oauth_token', 'apiProvider': 'firstParty',
                    'email': 'synthetic@example.invalid', 'accessToken': 'synthetic-private'}
            return {'exit_code': 0, 'stdout': json.dumps(data)}
        with patch('shutil.which', return_value='present'):
            result = s.inventory(run, lambda name: name, {})
        public = json.dumps(result)
        self.assertNotIn('synthetic', public)
        self.assertEqual(next(p for p in result['providers'] if p['cli'] == 'claude')['auth'], 'SUBSCRIPTION_LOGIN')
        self.assertEqual(next(p for p in result['providers'] if p['cli'] == 'gemini')['auth'], 'UNKNOWN')
        self.assertIn('qwen', result['excluded'])

    def test_additional_installed_clients_remain_unverified_without_probing(self):
        names = ('mimo', 'cursor', 'windsurf', 'cline', 'codebuff', 'freebuff', 'zed', 'ollama')
        with patch('shutil.which', side_effect=lambda cli: cli if cli in names else None):
            result = s.inventory(lambda *args, **kwargs: self.fail('Unsupported adapter was probed'),
                                 lambda cli: cli, {})
        for cli in names:
            row = next(row for row in result['providers'] if row['cli'] == cli)
            self.assertTrue(row['installed'])
            self.assertEqual((row['adapter'], row['auth'], row['access']),
                             ('UNVERIFIED', 'UNKNOWN', 'NOT_PROBED'))
            self.assertIsNone(row['quota_remaining'])
        self.assertFalse(any(row['cli'] == 'openrouter' for row in result['providers']))

    def test_dynamic_host_registry_has_only_safe_hints_and_preserves_false_install(self):
        custom = {'key': 'custom-future-host', 'display_name': 'Future Custom Host',
                  'installed': True, 'enabled': True, 'is_custom': True,
                  'skills_dir': 'private-path', 'extra': 'synthetic-private-secret'}
        absent = dict(custom, key='registered-not-installed', installed=False, enabled=False)
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return {'exit_code': 0, 'stdout': json.dumps([custom, absent])}
        with patch('shutil.which', side_effect=lambda cli: cli if cli == 'skills-manager-cli' else None):
            snapshot = s.inventory(run, lambda cli: cli, {'public': 'environment'})
        registry = snapshot['host_clients']
        self.assertEqual(calls, [(['skills-manager-cli', 'agents', 'list', '--json'],
                                 {'timeout': 30, 'env': {'public': 'environment'}})])
        self.assertEqual(registry['status'], 'REGISTRY_METADATA')
        self.assertEqual(registry['clients'][0]['key'], custom['key'])
        self.assertTrue(registry['clients'][0]['custom'])
        self.assertFalse(registry['clients'][1]['host_reported_installed'])
        self.assertFalse(registry['clients'][1]['enabled'])
        self.assertEqual(registry['clients'][0]['access'], 'UNKNOWN')
        self.assertEqual(registry['clients'][0]['adapter'], 'UNKNOWN')
        self.assertIsNone(registry['clients'][0]['quota_remaining'])
        self.assertNotIn('private', json.dumps(snapshot))
        self.assertEqual(s.route(snapshot, 'SIMPLE')['status'], 'BLOCKED')

    def test_host_registry_absence_or_malformed_metadata_never_creates_clients(self):
        with patch('shutil.which', return_value=None):
            self.assertEqual(s.host_registry(None, None, {})['status'], 'NOT_INSTALLED')
        valid = {'key': 'known', 'display_name': 'Known', 'installed': True, 'enabled': True, 'is_custom': False}
        for payload in ('invalid json', '{}', 'null', '[null]',
                        json.dumps([valid, dict(valid, installed='yes')]),
                        json.dumps([dict(valid, display_name='Unsafe\nName')]),
                        json.dumps([dict(valid, key='bad;command')])):
            with patch('shutil.which', return_value='manager'):
                result = s.host_registry(lambda *args, **kwargs: {'exit_code': 0, 'stdout': payload}, lambda cli: cli, {})
            self.assertEqual(result['status'], 'UNAVAILABLE')
            self.assertEqual(result['clients'], [])
        with patch('shutil.which', return_value='manager'):
            result = s.host_registry(lambda *args, **kwargs: {'exit_code': 1, 'stdout': json.dumps([valid])}, lambda cli: cli, {})
        self.assertEqual(result['clients'], [])

    def test_opencode_public_catalogue_never_proves_account_or_task_access(self):
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return {'exit_code': 0, 'stdout': 'opencode/example-free\nopenrouter/vendor/model:free\ninvalid output\n'}
        with patch('shutil.which', side_effect=lambda cli: cli if cli == 'opencode' else None):
            result = s.inventory(run, lambda cli: cli, {})
        self.assertEqual(calls, [['opencode', '--pure', 'models']])
        row = next(row for row in result['providers'] if row['cli'] == 'opencode')
        self.assertEqual([entry['id'] for entry in row['models']],
                         ['opencode/example-free', 'openrouter/vendor/model:free'])
        self.assertEqual((row['auth'], row['access']), ('UNKNOWN', 'NOT_PROBED'))
        self.assertTrue(all(entry['quality_tier'] == 'UNASSESSED' for entry in row['models']))
        self.assertEqual(s.route(result, 'SIMPLE')['status'], 'BLOCKED')

    def test_openrouter_requires_free_suffix_and_every_advertised_price_zero(self):
        valid = {'id': 'vendor/model:free', 'pricing': {'prompt': '0', 'completion': '0.0', 'request': 0, 'image': '0'},
                 'context_length': 32000, 'supported_parameters': ['tools', 'reasoning'],
                 'architecture': {'input_modalities': ['text', 'image'], 'output_modalities': ['text']}}
        result = s.openrouter_free_models({'data': [valid]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['input_modalities'], ['text', 'image'])
        self.assertEqual(result[0]['supported_parameters'], ['tools', 'reasoning'])
        self.assertEqual(result[0]['context_length'], 32000)
        self.assertEqual(result[0]['access'], 'NOT_PROBED')
        for price in (None, '', 'garbage', True, 'NaN', 'Infinity', '-1', '0.00001'):
            for key in ('prompt', 'completion', 'image', 'request', 'future_fee'):
                bad = copy.deepcopy(valid)
                bad['pricing'][key] = price
                with self.subTest(key=key, price=price):
                    self.assertEqual(s.openrouter_free_models({'data': [bad]}), [])
        for pricing in (None, {}, [], {'prompt': '0'}, {'completion': '0'}):
            self.assertEqual(s.openrouter_free_models({'data': [dict(valid, pricing=pricing)]}), [])
        self.assertEqual(s.openrouter_free_models({'data': [dict(valid, id='vendor/paid')]}), [])
        for payload in (None, [], {}, {'data': None}, {'data': [None]}, {'data': []}):
            self.assertEqual(s.openrouter_free_models(payload), [])

    def test_openrouter_get_is_optional_bounded_and_never_authenticated(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = s.OPENROUTER_MODELS_URL
        response.read.return_value = b'{"data": []}'
        with patch('urllib.request.urlopen', return_value=response) as fetch:
            row = s.openrouter_catalogue()
        fetch.assert_called_once_with(s.OPENROUTER_MODELS_URL, timeout=15)
        response.read.assert_called_once_with(s.CATALOGUE_MAX_BYTES + 1)
        self.assertEqual(row['catalogue'], 'PUBLIC_METADATA_VERIFIED')
        self.assertEqual((row['adapter'], row['auth'], row['access']), ('UNVERIFIED', 'UNKNOWN', 'NOT_PROBED'))
        response.read.return_value = b'x' * 11
        with patch('urllib.request.urlopen', return_value=response), patch.object(s, 'CATALOGUE_MAX_BYTES', 10):
            self.assertEqual(s.openrouter_catalogue()['catalogue'], 'UNAVAILABLE')
        response.geturl.return_value = 'https://example.invalid/models'
        with patch('urllib.request.urlopen', return_value=response):
            self.assertEqual(s.openrouter_catalogue()['catalogue'], 'UNAVAILABLE')
        with patch('urllib.request.urlopen', side_effect=OSError('unavailable')):
            self.assertEqual(s.openrouter_catalogue()['catalogue'], 'UNAVAILABLE')
        with patch('shutil.which', return_value=None), patch.object(s, 'openrouter_catalogue', return_value=row) as fetch:
            inventory = s.inventory(None, None, {}, include_openrouter=True)
        fetch.assert_called_once_with()
        self.assertEqual(inventory['providers'][-1]['cli'], 'openrouter')

    def test_invalid_usage_payload_is_not_metadata_verification(self):
        for value in (None, [], {}, {'status': 'SUCCESS', 'command': None},
                      {'status': 'SUCCESS', 'command': {'name': 'usage', 'data': {'groups': None}}}):
            self.assertEqual(s.agy_groups(value), [])
        groups = s.agy_groups({'status': 'SUCCESS', 'command': {'name': 'usage', 'data': {
            'groups': [{'name': 'Gemini Models', 'buckets': [{'remaining_fraction': .8}, None]}]}}})
        self.assertIsNone(s.remaining(groups[0]))

    def test_usage_counts_distinct_attempts_and_requires_coverage_manifest(self):
        row = {'provider': 'agy', 'session': 'worker', 'attempt': 1,
               'usage': dict(input_tokens=20, output_tokens=5, thinking_tokens=3, cache_read_tokens=7, total_tokens=35)}
        retry = dict(row, attempt=2)
        result = s.usage_summary([row, row, retry], [('agy', 'worker', 1), ('agy', 'worker', 2)])
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(result['totals']['input_tokens'], 40)
        self.assertTrue(result['complete'])
        self.assertFalse(s.usage_summary([row])['complete'])
        self.assertFalse(s.usage_summary([row], [('agy', 'worker', 1), ('codex', 'manager', 1)])['complete'])
        bad = dict(row, usage={'input_tokens': None})
        with self.assertRaises(ValueError):
            s.usage_summary([row, bad])
        self.assertIsNone(s.usage_summary([bad])['totals']['input_tokens'])
        self.assertIsNone(s.usage_summary([dict(row, usage=[1])])['totals']['input_tokens'])
        parent = dict(row, session='parent', includes_children=True)
        result = s.usage_summary([parent, row])
        self.assertEqual(result['totals']['input_tokens'], 20)
        self.assertFalse(result['complete'])

    def test_usage_rejects_unknown_child_coverage_and_invalid_identity(self):
        row = {'provider': 'agy', 'session': 'worker', 'attempt': 1, 'usage': {}}
        for changes in ({'includes_children': None}, {'includes_children': []},
                        {'provider': None}, {'session': ''}, {'attempt': True}, {'attempt': 0}):
            with self.assertRaises(ValueError):
                s.usage_summary([dict(row, **changes)])

    def test_native_launch_uses_actual_tui_and_keeps_prompt_out_of_terminal_parser(self):
        argv = s.native_launch('.', '/tmp/native.json', 'wt.exe', 'python.exe', 'subscriptions.py')
        self.assertIn('--interactive', argv)
        with self.assertRaises(RuntimeError):
            s.native_launch('.', 'native.json', None, 'python', 'subscriptions.py')
        with self.assertRaises(ValueError):
            s.native_launch('.', 'native;bad.json', 'wt.exe', 'python', 'subscriptions.py')

    def test_catalogue_and_exit_zero_do_not_prove_model_entitlement(self):
        selected = {'model': 'gemini-3.8-flash-medium'}
        for payload in ({'status': 'SUCCESS', 'response': ''},
                        {'status': 'SUCCESS', 'response': None, 'usage': [1]},
                        {'status': 'SUCCESS', 'response': 'READY', 'denied_actions': [{}]},
                        {'status': 'QUOTA_EXHAUSTED', 'response': 'READY'}):
            result = s.probe_model(selected, lambda *a, **kw: {'exit_code': 0, 'stdout': json.dumps(payload)}, lambda n: n, {})
            self.assertEqual(result['state'], 'UNVERIFIED')
        result = s.probe_model(selected, lambda *a, **kw: {'exit_code': 0, 'stdout': json.dumps({'status': 'SUCCESS', 'response': 'READY'})}, lambda n: n, {})
        self.assertEqual(result['state'], 'AVAILABLE')
        self.assertIsNone(result['usage']['input_tokens'])


if __name__ == '__main__':
    unittest.main()
