import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from runtime import plan
from runtime.legacy import POINTERS, legacy


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout


class LegacyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'app'
        (self.root / '.factory/runs').mkdir(parents=True)
        (self.root / '.factory/runs/handoff-1.json').write_text('{}')
        (self.root / '.factory-bootstrap.json').write_text('{}')
        (self.root / '.gitignore').write_bytes(b'build/\r\n.factory/runs/\r\n.factory/\r\n.store-automation/\r\n')
        (self.root / 'user.txt').write_text('keep')

    def add_brain(self):
        (self.root / '.project-brain/tasks').mkdir(parents=True)
        (self.root / '.project-brain/tasks/PB-004.md').write_text('# PB-004\n## Status\nREADY\n')
        (self.root / 'PROJECT_BRAIN.md').write_text('# goal\n')
        (self.root / 'AGENTS.md').write_text('# Rules\n\nkeep this\n\n' + POINTERS[0])

    def make_plan(self):
        plan.init(self.root)  # .gitignore still ignores the plan here, so init refuses only under git

    def test_artifacts_only_are_removed_without_a_plan(self):
        preview = legacy(self.root)
        self.assertEqual((preview['status'], preview['applied'], preview['files'], preview['extract_first']),
                         ('LEGACY_FOUND', False, 2, []))
        done = legacy(self.root, apply=True)
        archive = Path(done['archive'])
        self.assertFalse((self.root / '.factory').exists() or (self.root / '.factory-bootstrap.json').exists())
        self.assertTrue((archive / '.factory/runs/handoff-1.json').is_file())
        self.assertNotIn(self.root, archive.parents)
        # The plan must be tracked: the old whole-directory ignore line goes too.
        self.assertEqual((self.root / '.gitignore').read_bytes(), b'build/\r\n')
        self.assertEqual((self.root / 'user.txt').read_text(), 'keep')
        self.assertEqual(legacy(self.root)['status'], 'CLEAN')

    def test_plan_carrying_system_is_kept_until_extracted_then_fully_retired(self):
        self.add_brain()
        self.assertEqual(plan.boot(self.root)[1][0], 'STATE: LEGACY')
        with self.assertRaisesRegex(ValueError, 'not extracted'):
            legacy(self.root, apply=True)
        self.assertTrue((self.root / '.project-brain').is_dir())
        self.make_plan()
        done = legacy(self.root, apply=True)
        self.assertTrue(done['applied'])
        for name in ('.project-brain', 'PROJECT_BRAIN.md', '.factory'):
            self.assertFalse((self.root / name).exists(), name)
        agents = (self.root / 'AGENTS.md').read_text()
        self.assertIn('keep this', agents)
        self.assertNotIn('project-brain', agents)
        self.assertIn(plan.POINTER_MARK, agents)

    def test_unknown_system_by_path_and_infrastructure_refused(self):
        (self.root / '.otheragent/state').mkdir(parents=True)
        (self.root / '.otheragent/state/todo.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'infrastructure'):
            legacy(self.root, extra=['.git'])
        self.make_plan()
        done = legacy(self.root, apply=True, extra=['.otheragent'])
        self.assertFalse((self.root / '.otheragent').exists())
        self.assertTrue((Path(done['archive']) / '.otheragent/state/todo.json').is_file())

    def test_archive_is_deleted_only_after_the_removal_is_committed(self):
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 't@example.com')
        git(self.root, 'config', 'user.name', 'T')
        git(self.root, 'add', '-f', '.factory-bootstrap.json', 'user.txt')
        git(self.root, 'commit', '-qm', 'old')
        done = legacy(self.root, apply=True)
        with self.assertRaisesRegex(ValueError, 'Commit the adoption first'):
            legacy(self.root, drop_archive=True)
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'chore(plan): adopt store-automation')
        self.assertEqual(legacy(self.root, drop_archive=True)['status'], 'DROPPED')
        self.assertFalse(Path(done['archive']).exists())
        # Tracked content survives in Git history.
        self.assertEqual(git(self.root, 'show', 'HEAD~1:.factory-bootstrap.json'), '{}')

    @unittest.skipUnless(os.name == 'nt', 'Windows refuses renaming a directory with open files')
    def test_open_legacy_file_aborts_without_partial_move(self):
        with open(self.root / '.factory/runs/handoff-1.json'):
            with self.assertRaises(OSError):
                legacy(self.root, apply=True)
        self.assertTrue((self.root / '.factory/runs/handoff-1.json').is_file())
        self.assertTrue((self.root / '.factory-bootstrap.json').is_file())


if __name__ == '__main__':
    unittest.main()
