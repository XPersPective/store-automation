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
            self.assertIn('runtime/plan.py', manifest)
            self.assertIn('LICENSE', manifest)
            self.assertFalse(any(name.startswith(('design/', 'tests/')) for name in manifest))
            # Agents read piped JSON as UTF-8 regardless of the console code page.
            project = Path(temp) / 'proje-şğ-日本'
            project.mkdir()
            result = subprocess.run([sys.executable, str(destination / 'store.py'),
                '--project', str(project), 'doctor'], cwd=temp, capture_output=True,
                encoding='utf-8', check=True)
            self.assertEqual(json.loads(result.stdout)['project'], str(project))
            missing = subprocess.run([sys.executable, str(destination / 'store.py'),
                '--project', str(project / 'absent'), 'doctor'], capture_output=True, encoding='utf-8')
            self.assertEqual((missing.returncode, json.loads(missing.stdout)['status']), (2, 'ERROR'))
            (destination / 'user.txt').write_text('preserve')
            with self.assertRaises(ValueError):
                build(Path(__file__).resolve().parents[1], destination)
            self.assertEqual((destination / 'user.txt').read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
