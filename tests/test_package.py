import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from package import build


class PackageTests(unittest.TestCase):
    def test_standalone_package_and_failed_replacement_preserve_files(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'skill'
            manifest = build(Path(__file__).resolve().parents[1], destination)
            self.assertIn('runtime/gate.py', manifest)
            self.assertFalse(any(name.startswith(('design/', 'tests/')) for name in manifest))
            result = subprocess.run([sys.executable, str(destination / 'store.py'),
                '--project', temp, 'doctor'], cwd=temp, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['status'], 'READY')
            (destination / 'user.txt').write_text('preserve')
            with self.assertRaises(ValueError):
                build(Path(__file__).resolve().parents[1], destination)
            self.assertEqual((destination / 'user.txt').read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
