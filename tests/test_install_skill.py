"""Installer checks use temporary destinations; no native host is launched."""
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

installer = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tool/install-skill.py'))


class InstallSkillTests(unittest.TestCase):
    def test_owned_old_version_upgrades_without_touching_project_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, target = base / 'source.md', base / 'skill'
            project = base / 'project/.project-brain/current.md'
            project.parent.mkdir(parents=True)
            project.write_text('existing project checkpoint')
            source.write_text('version: 2.1.0')
            with patch.dict(installer['install'].__globals__, files=lambda: {'SKILL.md': source}):
                installer['install']([target])
                source.write_text('version: 2.2.0')
                installer['install']([target])
            self.assertEqual((target / 'SKILL.md').read_text(), 'version: 2.2.0')
            self.assertEqual(project.read_text(), 'existing project checkpoint')

    def test_discovery_uses_presence_and_preserves_data_dir_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.dict(os.environ, {'CODEX_HOME': str(home / 'custom-codex'),
                                        'MINIMAX_DATA_DIR': str(home / 'custom-minimax')}, clear=True), \
                    patch('shutil.which', side_effect=lambda name: name if name in ('codex', 'mcode', 'qwen') else None):
                found = installer['discover'](home)
            self.assertEqual(set(found), {'codex', 'mcode', 'qwen', 'agents'})
            self.assertEqual(found['codex'], home / 'custom-codex/skills/store-automation')
            self.assertEqual(found['mcode'], home / 'custom-minimax/skills/store-automation')

    def test_profile_folders_do_not_prove_host_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for name in ('.cursor', '.windsurf', '.cline', '.claude'):
                (home / name).mkdir()
            with patch('shutil.which', return_value=None):
                self.assertEqual(set(installer['discover'](home)), {'agents'})

    def test_known_editor_and_extension_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            exe = home / 'AppData/Local/Programs/Antigravity IDE/Antigravity IDE.exe'
            exe.parent.mkdir(parents=True)
            exe.touch()
            (home / '.vscode/extensions/saoudrizwan.claude-dev-1.0').mkdir(parents=True)
            with patch('shutil.which', return_value=None):
                found = installer['discover'](home)
            self.assertEqual(set(found), {'antigravity-ide', 'cline', 'agents'})
            self.assertEqual(found['antigravity-ide'], home / '.gemini/config/skills/store-automation')

    def test_all_destinations_preflight_before_any_resource_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'first', Path(tmp) / 'second'
            installer['install']([second])
            changed = second / 'SKILL.md'
            changed.write_text('user changes', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'modified/unowned'):
                installer['install']([first, second])
            self.assertFalse(first.exists())
            self.assertEqual(changed.read_text(), 'user changes')

    def test_linked_ancestor_refused_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            outside, link = base / 'outside', base / 'alias'
            outside.mkdir()
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('Directory symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'Linked'):
                installer['install']([link / 'skills/store-automation'])
            self.assertEqual(list(outside.iterdir()), [])

    def test_non_directory_destination_preflight_preserves_other_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bad = base / 'bad'
            bad.mkdir()
            (bad / 'runtime').write_text('user file')
            with self.assertRaisesRegex(ValueError, 'Non-directory'):
                installer['install']([base / 'first', bad])
            self.assertFalse((base / 'first').exists())
            self.assertEqual((bad / 'runtime').read_text(), 'user file')


if __name__ == '__main__':
    unittest.main()
