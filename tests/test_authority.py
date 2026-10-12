import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tool import dispatch as authority


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = {'task_id': 'PB-001', 'risk': 'LOW', 'complexity': 'SIMPLE',
            'persona': {'role': 'reviewer'}, 'permissions': {'write': False},
            'delegation': {'context_budget_chars': 1000, 'output_budget_tokens': 100, 'reason': 'bounded review'}}
        self.route = {'provider': 'codex', 'model': 'luna', 'effort': 'low',
            'quality_tier': 0, 'remaining_fraction': .5, 'quota_group': 'shared'}

    def test_high_risk_cannot_use_lightweight_model(self):
        self.task['risk'] = 'HIGH'
        with self.assertRaises(ValueError):
            authority.assignment(self.root, self.task, self.route, 'hash')
        self.assertEqual(list(self.root.rglob('assignment-*.json')), [])

    def test_exclusive_bucket_releases_after_failure(self):
        directory = self.root / 'admissions'
        with self.assertRaisesRegex(RuntimeError, 'failure'):
            with authority.admit(self.route, self.root, 'first', directory):
                with self.assertRaises(RuntimeError):
                    with authority.admit(self.route, self.root, 'second', directory):
                        self.fail('concurrent admission')
                raise RuntimeError('failure')
        with authority.admit(self.route, self.root, 'third', directory):
            self.assertEqual(len(list(directory.glob('*.lock'))), 1)
        self.assertEqual(list(directory.glob('*.lock')), [])

    def test_link_and_escape_are_rejected(self):
        with self.assertRaises(ValueError):
            authority.owned_path(self.root, '../outside.json')

    def test_assignment_is_unique_and_missing_quota_fails(self):
        a, _ = authority.assignment(self.root, self.task, self.route, 'hash')
        b, _ = authority.assignment(self.root, self.task, self.route, 'hash')
        self.assertNotEqual(a, b)
        self.route['remaining_fraction'] = None
        with self.assertRaises(ValueError):
            authority.assignment(self.root, self.task, self.route, 'hash')

    def test_handoff_keeps_full_state_by_reference(self):
        path = authority.handoff(self.root, 'PB-001', 'hash', [], 'Run next check', 'B' * 9000, 'G' * 3000)
        data = json.loads(path.read_text())
        reference = self.root / data['full_state']['path']
        self.assertTrue(data['summary_shortened'])
        self.assertEqual(len(json.loads(reference.read_text())['brain']), 9000)
        self.assertEqual(authority.hashlib.sha256(reference.read_bytes()).hexdigest(), data['full_state']['sha256'])

    def test_live_controller_cannot_be_reconciled(self):
        lock = authority.owned_path(self.root, '.factory/team.lock')
        lock.write_text(json.dumps({'pid': 123, 'owner': 'x'}))
        with patch.object(authority, 'absent', return_value=False):
            with self.assertRaises(RuntimeError):
                authority.reconcile_team(self.root)
        self.assertTrue(lock.exists())
