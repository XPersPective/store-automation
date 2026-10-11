import copy
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

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

    def test_shared_bucket_reserve_excludes_all_gemini_siblings(self):
        self.groups[0]['buckets'][1]['remaining_fraction'] = .10
        result = s.route(self.snapshot, 'COMPLEX')
        self.assertEqual(result['selected']['model'], 'claude-opus-5-5-high')
        self.assertTrue(all(c['quota_group'] != 'Gemini Models' for c in result['candidates']))
        self.groups[1]['buckets'][0]['remaining_fraction'] = 0
        self.assertEqual(s.route(self.snapshot, 'COMPLEX')['status'], 'BLOCKED')

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
