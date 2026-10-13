import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from runtime import plan
from runtime.legacy import BRAIN_POINTER, legacy


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

    def test_dry_run_then_apply_moves_old_state_out_and_keeps_user_files(self):
        preview = legacy(self.root)
        self.assertEqual((preview['status'], preview['applied'], preview['files']), ('LEGACY_FOUND', False, 2))
        self.assertTrue((self.root / '.factory').exists())
        done = legacy(self.root, apply=True)
        archive = Path(done['archive'])
        self.assertFalse((self.root / '.factory').exists() or (self.root / '.factory-bootstrap.json').exists())
        self.assertTrue((archive / '.factory/runs/handoff-1.json').is_file())
        self.assertNotIn(self.root, archive.parents)
        # The plan must be tracked: the old whole-directory ignore line goes too.
        self.assertEqual((self.root / '.gitignore').read_bytes(), b'build/\r\n')
        self.assertEqual((self.root / 'user.txt').read_text(), 'keep')
        self.assertEqual(legacy(self.root)['status'], 'CLEAN')

    def test_project_brain_plan_converts_to_store_automation(self):
        brain = self.root / '.project-brain'
        (brain / 'tasks').mkdir(parents=True)
        (brain / 'decisions').mkdir()
        (brain / 'config.yaml').write_text('schema_version: 4\n\ngit:\n  commit: "auto"\n  push: "manual"\n'
                                           '\ncommands:\n  test: "flutter test"\n')
        (brain / 'current.md').write_text('# Current Architecture\n\n## Map\n- `lib/` — app\n', encoding='utf-8')
        (brain / 'target.md').write_text('# Target Architecture\nStatus: CONFIRMED\n\n## Goal\nilaç takibi\n',
                                         encoding='utf-8')
        (brain / 'decisions/ADR-001.md').write_text('# ADR-001\nSee PB-004.\n')
        (brain / 'tasks/PB-004.md').write_text('# PB-004 — Reminder\nStatus: READY\nDepends: PB-001, PB-005\n\n'
                                               '## Acceptance\n- [ ] works\n', encoding='utf-8')
        (brain / 'tasks/PB-005.md').write_text('# PB-005 — Export\nStatus: PLANNED\nDepends: -\n', encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('# Rules\n\n' + BRAIN_POINTER)
        preview = legacy(self.root)
        self.assertIn('tasks/SA-004.md', preview['converted'])
        self.assertFalse(plan.plan_exists(self.root))
        legacy(self.root, apply=True)
        self.assertFalse(brain.exists())
        task = plan.parse_task(self.root / '.store-automation/tasks/SA-004.md')
        self.assertEqual((task['title'], task['deps']), ('Reminder', ['SA-005']))
        self.assertIn('closed dependency PB-001', task['text'])
        product = (self.root / '.store-automation/product.md').read_text(encoding='utf-8')
        self.assertIn('Status: CONFIRMED', product)
        self.assertIn('## Core Journeys', product)
        config = plan.load_config(self.root)
        self.assertEqual((config['commands']['test'], config['git']['push']), ('flutter test', 'ask'))
        self.assertIn('SA-004', (self.root / '.store-automation/decisions/ADR-001.md').read_text())
        agents = (self.root / 'AGENTS.md').read_text()
        self.assertIn(plan.POINTER_MARK, agents)
        self.assertNotIn('project-brain', agents)
        # Untagged acceptance stays visible as a validate failure, never guessed.
        self.assertTrue(any('kind tag' in line for line in plan.validate(self.root)[1]))

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
