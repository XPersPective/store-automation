"""Protocol text and CLI must not drift apart (the v3 review found exactly this)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / 'SKILL.md', *sorted((ROOT / 'references').glob('*.md'))]


def subcommands():
    text = (ROOT / 'store.py').read_text(encoding='utf-8')
    names = set(re.findall(r"sub\.add_parser\('([a-z-]+)'", text))
    names |= set(re.findall(r"'([a-z]+)'", re.search(r"for name in \(([^)]*)\)", text).group(1)))
    return names


class DocsTests(unittest.TestCase):
    def test_every_documented_command_exists_and_every_command_is_documented(self):
        commands = subcommands()
        used = set()
        for doc in DOCS:
            used |= set(re.findall(r'`SA ([a-z-]+)', doc.read_text(encoding='utf-8')))
        self.assertEqual(sorted(used - commands), [], 'docs mention commands the CLI lacks')
        runtime = (ROOT / 'references/runtime.md').read_text(encoding='utf-8')
        documented = set(re.findall(r'^\| `([a-z-]+)', runtime, re.M))
        self.assertEqual(sorted(commands - documented), [], 'commands missing from runtime.md')

    def test_relative_links_resolve(self):
        for doc in DOCS:
            for target in re.findall(r'\]\(([^)#:]+\.md)\)', doc.read_text(encoding='utf-8')):
                self.assertTrue((doc.parent / target).is_file(), f'{doc.name} -> {target}')

    def test_version_is_one_number(self):
        """Content never changes under an unchanged version (audit m12)."""
        skill = re.search(r'version: "([^"]+)"', (ROOT / 'SKILL.md').read_text(encoding='utf-8')).group(1)
        store = re.search(r"VERSION = '([^']+)'", (ROOT / 'store.py').read_text(encoding='utf-8')).group(1)
        self.assertEqual(skill, store)

    def test_skill_entry_stays_small(self):
        self.assertLessEqual(len((ROOT / 'SKILL.md').read_text(encoding='utf-8').splitlines()), 90)


if __name__ == '__main__':
    unittest.main()
