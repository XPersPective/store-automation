import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()))

from tool import subscriptions as s


class Tree:
    def __init__(self):
        self.proc = None
        self.closed = threading.Event()
    def close(self):
        self.closed.set()


class DiscoveryChecks(unittest.TestCase):
    def test_report_metadata_is_sanitized_and_never_grants_quota_or_access(self):
        from tool import native_agents, sessions
        tree = Tree()
        class Acp:
            def __init__(self, *args, **kwargs): pass
            def report(self):
                return {'inference': False, 'billing': 'SUBSCRIPTION', 'quota': {'remaining': 99},
                        'models': [{'id': 'm:minimax:MiniMax-M3:v:', 'name': 'M3'},
                                   {'id': '../private', 'name': 'rejected'},
                                   {'id': 'future model', 'name': 'rejected'}],
                        'efforts': ['low', 'high', '../private'],
                        'modes': ['plan', 'auto', '../private']}
        with patch.object(native_agents, 'AcpMetadata', Acp), \
             patch.object(sessions, 'ProcessTree', return_value=tree), \
             patch('shutil.which', return_value='kimi.exe'):
            result = s._acp_catalogue('kimi', lambda cli: 'kimi.exe', {})
        self.assertEqual(result['models'], [{'id': 'm:minimax:MiniMax-M3:v:', 'name': 'M3'}])
        self.assertEqual(result['efforts'], [{'id': 'low'}, {'id': 'high'}])
        self.assertEqual(result['mode_options'], [{'id': 'plan'}, {'id': 'auto'}])
        self.assertEqual(result['catalogue'], 'CLI_METADATA_VERIFIED')
        self.assertNotIn('quota', result)
        self.assertNotIn('billing', result)
        self.assertNotIn('private', json.dumps(result))
        self.assertTrue(tree.closed.is_set())

    def test_unsupported_acp_client_has_bounded_timeout_and_cleanup_errors_propagate(self):
        from tool import native_agents, sessions
        tree = Tree()
        class Acp:
            def __init__(self, *args, **kwargs):
                tree.closed.wait(2)
                raise RuntimeError('private status text')
        with patch.object(native_agents, 'AcpMetadata', Acp), \
             patch.object(sessions, 'ProcessTree', return_value=tree), \
             patch('shutil.which', return_value='kimi.exe'):
            started = time.monotonic()
            result = s._acp_catalogue('kimi', lambda cli: 'kimi.exe', {}, timeout=.03)
        self.assertLess(time.monotonic() - started, .5)
        self.assertEqual(result['error'], 'TimeoutError')
        self.assertNotIn('private', json.dumps(result))
        class BrokenTree(Tree):
            def close(self): raise RuntimeError('containment is unverified')
        with patch.object(native_agents, 'AcpMetadata', Acp), \
             patch.object(sessions, 'ProcessTree', BrokenTree), \
             patch('shutil.which', return_value='kimi.exe'):
            with self.assertRaisesRegex(RuntimeError, 'containment is unverified'):
                s._acp_catalogue('kimi', lambda cli: 'kimi.exe', {}, timeout=.03)

    def test_acp_catalogue_never_grants_entitlement_or_route_eligibility(self):
        now = s.datetime.now(s.timezone.utc)
        payload = {'models': [{'id': 'm:minimax:MiniMax-M3:v:', 'name': 'M3'}],
                   'efforts': ['low'], 'mode_options': ['plan'], 'model_selector': True,
                   'catalogue': 'CLI_METADATA_VERIFIED'}
        with patch('shutil.which', side_effect=lambda name: name if name in ('mcode', 'kimi') else None), \
             patch.object(s, '_acp_catalogue', return_value=payload) as probe:
            snapshot = s.inventory(lambda *args, **kwargs: self.fail('No unsupported CLI probe expected'),
                                   lambda name: name, {})
        self.assertEqual(probe.call_count, 2)
        for cli in ('mcode', 'kimi'):
            row = next(row for row in snapshot['providers'] if row['cli'] == cli)
            self.assertEqual(row['catalogue'], 'CLI_METADATA_VERIFIED')
            self.assertEqual((row['auth'], row['access'], row['billing']),
                             ('UNKNOWN', 'NOT_PROBED', 'UNVERIFIED'))
            self.assertIsNone(row['quota_remaining'])
        self.assertEqual(s.route(snapshot, 'SIMPLE')['status'], 'BLOCKED')
        self.assertGreaterEqual(snapshot['captured_at'], now.isoformat())

    def test_mcode_uses_official_package_entrypoint_and_native_node(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / 'node_modules' / '@minimax-ai' / 'code' / 'cli.js'
            script.parent.mkdir(parents=True)
            script.write_text('', encoding='utf-8')
            with patch('shutil.which', return_value=str(root / 'mcode.cmd')):
                argv = s._acp_argv('mcode', lambda name: 'node.exe' if name == 'node' else str(root / 'mcode.cmd'))
        self.assertEqual(argv[0], 'node.exe')
        self.assertEqual(argv[-1], 'acp')
        self.assertIn('@minimax-ai', argv[1])


if __name__ == '__main__':
    unittest.main()

