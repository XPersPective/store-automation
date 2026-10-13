from pathlib import Path
import sys
import tempfile
import unittest

from runtime.receipts import read_record
from runtime.verification import measured_usage, release_readback, run_check


class VerificationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'source.txt').write_text('input')

    def test_actual_command_success_failure_and_mutation(self):
        for code, expected in [
            ('print("real execution")', 'PASS'),
            ('raise SystemExit(2)', 'FAIL'),
            ('from pathlib import Path; Path("source.txt").write_text("changed")', 'FAIL')]:
            result = run_check(self.root, [sys.executable, '-c', code], ['source.txt'])
            self.assertEqual(result['state'], expected)
            self.assertTrue(read_record(self.root, result['reference'])['duration_seconds'] > 0)

    def test_real_timeout_kills_owned_descendant_before_delayed_write(self):
        marker = self.root / 'orphan.txt'
        child = 'import time; from pathlib import Path; time.sleep(1.5); Path("orphan.txt").write_text("bad")'
        parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); time.sleep(20)'
        result = run_check(self.root, [sys.executable, '-c', parent], ['source.txt'], timeout=.15)
        self.assertEqual(result['exit_code'], 124)
        import time
        time.sleep(1.7)
        self.assertFalse(marker.exists())

    def test_release_exit_success_cannot_replace_exact_remote_readback(self):
        expected = dict(platform='android', account='selected', app='com.example.test',
                        channel='internal', version='3', artifact_sha256='digest', state='AVAILABLE')
        observed = dict(expected, state='UPLOADED', readback_reference='tool:1',
                        observed_at='2026-10-13T12:00:00Z', provenance='verified')
        self.assertEqual(release_readback(expected, observed)['status'], 'UNVERIFIED')
        observed.update(state='AVAILABLE', availability_reference='tool:public-url')
        self.assertEqual(release_readback(expected, observed)['status'], 'MATCHED')
        for key in ('account', 'app', 'channel', 'version', 'artifact_sha256'):
            self.assertEqual(release_readback(expected, dict(observed, **{key:'wrong'}))['status'], 'BLOCKED')
        for key in ('readback_reference', 'observed_at', 'availability_reference'):
            with self.assertRaises(ValueError):
                release_readback(expected, dict(observed, **{key: True}))
        with self.assertRaises(ValueError):
            release_readback(expected, dict(observed, observed_at='2026-10-13T12:00:00'))

    def test_usage_missing_retry_and_inclusive_parent_never_fabricate_total(self):
        one = dict(id='parent', usage_scope='disjoint_last_turn', usage=dict(input_tokens=10,output_tokens=2))
        two = dict(id='worker', usage_scope='disjoint_last_turn', usage=dict(input_tokens=20,output_tokens=3))
        self.assertEqual(measured_usage([one,two], ['parent','worker'])['totals'],
                         dict(input_tokens=30,output_tokens=5))
        self.assertIsNone(measured_usage([one,two], ['parent','worker','retry'])['totals'])
        self.assertIsNone(measured_usage([dict(one,usage_scope='includes_children'),two], ['parent','worker'])['totals'])
        with self.assertRaises(ValueError):
            measured_usage([one,one], ['parent'])


if __name__ == '__main__':
    unittest.main()
