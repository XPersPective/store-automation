import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from runtime.legacy import legacy
from runtime.receipts import read_record


class LegacyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'app'
        (self.root / '.factory/runs').mkdir(parents=True)
        (self.root / '.factory/runs/handoff-1.json').write_text('{}')
        (self.root / '.factory-bootstrap.json').write_text('{}')
        (self.root / '.gitignore').write_bytes(b'build/\r\n.factory/runs/\r\n.factory/\r\n')
        (self.root / 'user.txt').write_text('keep')

    def test_dry_run_then_apply_moves_old_state_out_and_keeps_user_files(self):
        plan = legacy(self.root)
        self.assertEqual((plan['status'], plan['applied'], plan['files']), ('LEGACY_FOUND', False, 2))
        self.assertTrue((self.root / '.factory').exists())
        done = legacy(self.root, apply=True)
        archive = Path(done['archive'])
        self.assertFalse((self.root / '.factory').exists() or (self.root / '.factory-bootstrap.json').exists())
        self.assertTrue((archive / '.factory/runs/handoff-1.json').is_file())
        self.assertNotIn(self.root, archive.parents)
        self.assertEqual((self.root / '.gitignore').read_bytes(), b'build/\r\n.store-automation/\r\n')
        self.assertEqual((self.root / 'user.txt').read_text(), 'keep')
        self.assertEqual(read_record(self.root, done['record'])['legacy'], ['.factory', '.factory-bootstrap.json'])
        self.assertEqual(legacy(self.root)['status'], 'CLEAN')

    def test_tracked_legacy_files_are_refused(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '-f', '.factory-bootstrap.json'], check=True)
        with self.assertRaisesRegex(ValueError, 'tracked'):
            legacy(self.root, apply=True)
        self.assertTrue((self.root / '.factory').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows refuses renaming a directory with open files')
    def test_open_legacy_file_aborts_without_partial_move(self):
        with open(self.root / '.factory/runs/handoff-1.json'):
            with self.assertRaises(OSError):
                legacy(self.root, apply=True)
        self.assertTrue((self.root / '.factory/runs/handoff-1.json').is_file())
        self.assertTrue((self.root / '.factory-bootstrap.json').is_file())


if __name__ == '__main__':
    unittest.main()
