import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime import receipts
from test_acceptance import example


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'app.py').write_text('before')
        self.task = example()[0]
        self.task['project'] = str(self.root)

    def assign(self, write=True, role='implementer'):
        self.task['permissions']['write'] = write
        ref = receipts.prepare(self.root, self.task, role, 'native-worker', ['app.py'])
        record = receipts.read_record(self.root, ref)
        report = {k: record[k] for k in ('task', 'project', 'attempt', 'role', 'provider', 'model', 'effort')}
        report.update(state='COMPLETED', changed_files=['app.py'] if write else [],
                      evidence=['observed output'], blockers=[], usage=None, next_action='Review')
        return ref, record, report

    def test_implementation_can_change_source_but_readonly_cannot(self):
        ref, record, report = self.assign()
        (self.root / 'app.py').write_text('authorized edit')
        result = receipts.finish(self.root, ref, report, output_files=['app.py'],
                                 native_reference='host-tool:result-1', observed_actor='native-worker',
                                 observed_state='COMPLETED', observer='coordinator')
        output = receipts.read_record(self.root, result)
        self.assertNotEqual(record['input_subject'], output['output_subject'])
        self.assertEqual(output['provenance'], 'declared')
        receipts.verify_snapshot(self.root, output['output_snapshot'])
        ref, record, report = self.assign(write=False, role='reviewer')
        (self.root / 'app.py').write_text('changed during readonly review')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            receipts.finish(self.root, ref, report, output_files=['app.py'],
                            native_reference='host:result-2', observed_actor='native-worker',
                            observed_state='COMPLETED', observer='coordinator')

    def test_private_paths_are_rejected_before_any_hashing(self):
        with patch.object(Path, 'open', side_effect=AssertionError('must not open')):
            for name in ('../outside', 'C:/auth.json', '.env', 'credentials/key.json',
                         'service-account.json', 'upload.jks', 'app.py:stream', 'a\\b',
                         '.env.', '.env ', 'secrets./a.json', 'NUL', 'aux.txt'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    receipts.snapshot(self.root, ['app.py', name])

    def test_manifest_source_and_record_tampering_rejected(self):
        snap = receipts.snapshot(self.root, ['app.py'])
        (self.root / 'app.py').write_text('after')
        with self.assertRaises(ValueError):
            receipts.verify_snapshot(self.root, snap)
        one = receipts.append_record(self.root, 'check', {'result': 1})
        two = receipts.append_record(self.root, 'check', {'result': 2})
        self.assertNotEqual(one['path'], two['path'])
        (self.root / one['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Changed'):
            receipts.read_record(self.root, one)

    def test_native_identity_and_task_cannot_be_borrowed(self):
        ref, _, report = self.assign()
        with self.assertRaisesRegex(ValueError, 'observer/actor'):
            receipts.finish(self.root, ref, report, output_files=['app.py'],
                            native_reference='other', observed_actor='foreign-worker',
                            observed_state='COMPLETED', observer='coordinator')
        self.task['project'] = str(self.root / 'other')
        with self.assertRaisesRegex(ValueError, 'another project'):
            receipts.prepare(self.root, self.task, 'implementer', 'worker', ['app.py'])

    def test_handoff_retains_partial_work_unknown_owner_and_pending_upload(self):
        ref, _, _ = self.assign()
        (self.root / 'app.py').write_text('partial work')
        (self.root / 'user.txt').write_text('unrelated user edit')
        for owner, external, expected in [
            ('active', 'not_started', 'RECONCILE_OWNER'),
            ('unknown', 'response_unknown', 'RECONCILE_OWNER'),
            ('absent', 'response_unknown', 'READBACK_FIRST'),
            ('absent', 'confirmed', 'INSPECT_DIFF')]:
            result = receipts.handoff(self.root, task_ref=ref, assignments=[ref],
                next_action='Inspect partial diff and reconcile',
                ownership=[dict(state=owner, reference='native-worker')],
                pending_external=[dict(state=external, readback='Query selected version')],
                public_files=['app.py'], notes='Preserve user.txt; no replay')
            self.assertEqual(receipts.read_record(self.root, result)['resume'], expected)
        self.assertEqual((self.root / 'user.txt').read_text(), 'unrelated user edit')
        self.assertEqual((self.root / 'app.py').read_text(), 'partial work')
        self.task['id'] = 'OTHER-TASK'
        foreign = receipts.prepare(self.root, self.task, 'implementer', 'worker', ['app.py'])
        with self.assertRaisesRegex(ValueError, 'another task'):
            receipts.handoff(self.root, task_ref=ref, assignments=[ref, foreign], next_action='x',
                ownership=[], pending_external=[], public_files=['app.py'], notes='n')


if __name__ == '__main__':
    unittest.main()
