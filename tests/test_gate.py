import copy
from pathlib import Path
import tempfile
import unittest
from runtime import receipts
from runtime.acceptance import fingerprint
from runtime.gate import gate
from test_acceptance import example


class GateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'source.py').write_text('example')
        self.task = example()[0]
        self.task.update(project=str(self.root), risk='LOW', independent_review=False)
        self.task['criteria'] = [dict(id='C1', description='Check', required=True, kinds=['machine'])]
        ref = receipts.prepare(self.root, self.task, 'implementer', 'worker', ['source.py'])
        assignment = receipts.read_record(self.root, ref)
        report = {k: assignment[k] for k in ('task', 'project', 'attempt', 'role', 'provider', 'model', 'effort')}
        report.update(state='COMPLETED', changed_files=[], evidence=[], blockers=[], next_action='Review')
        implementation = receipts.finish(self.root, ref, report, output_files=['source.py'],
            native_reference='synthetic:native', observed_actor='worker', observed_state='COMPLETED', observer='controller')
        source = receipts.snapshot(self.root, ['source.py'])
        check = receipts.append_record(self.root, 'check', dict(state='PASS', source_stable=True, cwd=str(self.root),
                    exit_code=0, input_snapshot=source))
        obs = receipts.append_record(self.root, 'observation', dict(id='O1', task=self.task['id'],
            project=str(self.root), task_hash=fingerprint(self.task), subject=source['subject'],
            criterion='C1', kind='machine', result='PASS', evidence=check, reference=check['path'],
            observer='controller', method='synthetic test', environment='temp', captured_at='2026-10-13'))
        self.bundle = dict(task=self.task, source=source, implementation=implementation, observations=[obs])
        self.attestations = [dict(record=r, observer='controller', method='test only',
            native_reference='synthetic:native', observed_at='2026-10-13', actor='worker', state='COMPLETED')
            for r in (implementation, obs)]

    def test_only_supervisor_attestation_and_current_bytes_accept(self):
        self.assertEqual(gate(self.root, self.bundle, [])['status'], 'UNVERIFIED')
        self.assertEqual(gate(self.root, self.bundle, self.attestations)['status'], 'ACCEPTED')
        (self.root / 'source.py').write_text('stale')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            gate(self.root, self.bundle, self.attestations)

    def test_foreign_native_outcome_and_record_tampering_rejected(self):
        bad = copy.deepcopy(self.attestations)
        bad[0]['actor'] = 'unrelated-session'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            gate(self.root, self.bundle, bad)
        (self.root / self.bundle['observations'][0]['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Changed'):
            gate(self.root, self.bundle, self.attestations)

    def test_identical_files_in_foreign_check_directory_do_not_accept(self):
        obs = receipts.read_record(self.root, self.bundle['observations'][0])
        evidence = receipts.read_record(self.root, obs['evidence'])
        evidence['cwd'] = str(self.root / 'other-project')
        obs['evidence'] = receipts.append_record(self.root, 'check', evidence)
        ref = receipts.append_record(self.root, 'observation', obs)
        self.bundle['observations'] = [ref]
        self.attestations[1]['record'] = ref
        with self.assertRaisesRegex(ValueError, 'current success'):
            gate(self.root, self.bundle, self.attestations)

    def test_changed_screenshot_invalidates_visual_evidence(self):
        self.task['criteria'][0]['kinds'] = ['visual']
        self.bundle['task'] = self.task
        ref = receipts.prepare(self.root, self.task, 'implementer', 'worker', ['source.py'])
        assignment = receipts.read_record(self.root, ref)
        report = {k: assignment[k] for k in ('task', 'project', 'attempt', 'role', 'provider', 'model', 'effort')}
        report.update(state='COMPLETED', changed_files=[], evidence=[], blockers=[], next_action='Review')
        self.bundle['implementation'] = self.attestations[0]['record'] = receipts.finish(self.root, ref, report,
            output_files=['source.py'], native_reference='synthetic:native', observed_actor='worker',
            observed_state='COMPLETED', observer='controller')
        (self.root / 'shot.png').write_bytes(b'seen')
        def observe(evidence):
            ref = receipts.append_record(self.root, 'observation', dict(id='V1', task=self.task['id'],
                project=str(self.root), task_hash=fingerprint(self.task), subject=self.bundle['source']['subject'],
                criterion='C1', kind='visual', result='PASS', evidence=receipts.append_record(self.root, 'observation', evidence),
                reference='shot.png', observer='controller', method='viewed', environment='temp', captured_at='2026-10-13'))
            self.bundle['observations'] = [ref]
            self.attestations[1]['record'] = ref
        observe(dict(note='screenshot shot.png'))
        with self.assertRaisesRegex(ValueError, 'Snapshot record required'):
            gate(self.root, self.bundle, self.attestations)
        observe(dict(artifacts=receipts.snapshot(self.root, ['shot.png'])))
        self.assertEqual(gate(self.root, self.bundle, self.attestations)['status'], 'ACCEPTED')
        (self.root / 'shot.png').write_bytes(b'edited')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            gate(self.root, self.bundle, self.attestations)

    def test_completed_outcome_cannot_hide_blocked_report(self):
        record = receipts.read_record(self.root, self.bundle['implementation'])
        record['report'].update(state='BLOCKED', blockers=['unfinished'])
        ref = receipts.append_record(self.root, 'outcome', record)
        self.bundle['implementation'] = ref
        self.attestations[0]['record'] = ref
        with self.assertRaisesRegex(ValueError, 'differs from report'):
            gate(self.root, self.bundle, self.attestations)


if __name__ == '__main__':
    unittest.main()
