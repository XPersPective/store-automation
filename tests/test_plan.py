from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime import plan

READY_TASK = """# {id} — Add greeting
Status: READY
Priority: P1
Tier: L
Risk: LOW
Milestone: M1
Depends: -
Owner:
Areas: `app.py`, `test_app.py`

## Objective
"selam desin" (user).

## Steps
1. In `app.py` add `greet()` returning "selam".

## Acceptance
- [ ] [machine] `greet() == "selam"` asserted by test_app.py

## Verify
- `python -m unittest test_app`

## External

## Evidence

## Review

## Notes
"""


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout


class Repo(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 't@example.com')
        git(self.root, 'config', 'user.name', 'T')
        (self.root / 'app.py').write_text('def greet():\n    return "selam"\n')
        (self.root / 'test_app.py').write_text(
            'import unittest, app\nclass T(unittest.TestCase):\n    def test(self):\n'
            '        self.assertEqual(app.greet(), "selam")\n')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'initial')

    def init_plan(self):
        self.assertEqual(plan.init(self.root)[0], 0)
        (self.root / '.store-automation/tasks/SA-001.md').write_text(READY_TASK.format(id='SA-001'), encoding='utf-8')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'chore(plan): baseline\n\nSA-Genesis: true\nSA-Current-Checkpoint: all')

    def boot(self):
        code, lines = plan.boot(self.root)
        self.assertEqual(code, 0)
        return lines


class PlanTests(Repo):
    def test_no_plan_then_init_creates_tracked_plan_and_agent_pointer(self):
        self.assertEqual(self.boot()[0], 'STATE: NO_PLAN')
        self.init_plan()
        self.assertIn(plan.POINTER_MARK, (self.root / 'AGENTS.md').read_text())
        tracked = git(self.root, 'ls-files', '.store-automation')
        self.assertIn('.store-automation/product.md', tracked)
        self.assertIn('.store-automation/tasks/SA-001.md', tracked)
        lines = self.boot()
        self.assertEqual(lines[0], 'STATE: RESUME')
        self.assertTrue(any(line.startswith('FOCUS SA-001') for line in lines))
        self.assertEqual(plan.init(self.root)[1][0], 'EXISTS: nothing overwritten')

    def test_ignored_plan_directory_is_refused(self):
        (self.root / '.gitignore').write_text('.store-automation/\n')
        code, lines = plan.init(self.root)
        self.assertEqual(code, 2)
        self.assertIn('gitignored', lines[0])

    def test_interrupted_dirty_and_readback_first_states(self):
        self.init_plan()
        self.assertEqual(plan.start(self.root, 'SA-001', 'small-model')[0], 0)
        (self.root / 'app.py').write_text('def greet():\n    return "sel"\n')
        lines = self.boot()
        self.assertEqual(lines[0], 'STATE: INTERRUPTED')
        self.assertTrue(any('owner small-model' in line for line in lines))
        (self.root / 'user.txt').write_text('user work')
        self.assertEqual(self.boot()[0], 'STATE: DIRTY')
        plan.append_section(self.root / '.store-automation/tasks/SA-001.md', 'External',
                            '- upload aab 1.0.0 | response_unknown | readback: fastlane supply track list')
        lines = self.boot()
        self.assertEqual(lines[0], 'STATE: READBACK_FIRST')
        self.assertTrue(any(line.startswith('EXTERNAL SA-001') for line in lines))

    def test_start_rules_and_second_writer_refused(self):
        self.init_plan()
        (self.root / '.store-automation/tasks/SA-002.md').write_text(READY_TASK.format(id='SA-002'), encoding='utf-8')
        self.assertEqual(plan.start(self.root, 'SA-001', 'a')[0], 0)
        code, lines = plan.start(self.root, 'SA-002', 'b')
        self.assertEqual(code, 2)
        self.assertIn('already IN_PROGRESS', lines[0])
        self.assertEqual(plan.start(self.root, '1', 'other')[0], 2)

    def test_takeover_of_abandoned_task_needs_a_recorded_reason(self):
        self.init_plan()
        plan.start(self.root, 'SA-001', 'crashed-model')
        code, lines = plan.start(self.root, 'SA-001', 'next-model')
        self.assertEqual(code, 2)
        self.assertIn('--takeover', lines[0])
        code, lines = plan.start(self.root, 'SA-001', 'next-model', takeover='session ended, no activity')
        self.assertEqual(code, 0, lines)
        task = plan.parse_task(self.root / '.store-automation/tasks/SA-001.md')
        self.assertEqual(task['owner'], 'next-model')
        self.assertIn('takeover from crashed-model by next-model', task['text'])

    def test_partial_checkpoint_and_map_entry_clear_advanced(self):
        self.init_plan()
        (self.root / 'tools.py').write_text('x = 1\n')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'tool')
        self.assertEqual(self.boot()[0], 'STATE: ADVANCED')
        current = self.root / '.store-automation/current.md'
        current.write_text(current.read_text(encoding='utf-8').replace(
            '## Map\n', '## Map\n- `tools.py` — helper\n'), encoding='utf-8')
        git(self.root, 'commit', '-qam', 'docs(plan): map tools\n\nSA-Current-Checkpoint: storage')
        self.assertEqual(self.boot()[0], 'STATE: RESUME')

    def test_missing_remote_is_visible(self):
        self.init_plan()
        self.assertTrue(any('no git remote' in line for line in self.boot()))

    def test_closed_task_is_recognised_from_git_history_only(self):
        self.init_plan()
        task = self.root / '.store-automation/tasks/SA-001.md'
        plan.set_header(task, 'Status', 'DONE')
        plan.append_section(task, 'Evidence', '- accept: DONE | digest=abc')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'feat: greet [SA-001]\n\nSA-Task: SA-001\nSA-Verification: local\nSA-Agent: m')
        task.unlink()
        git(self.root, 'commit', '-qam', 'chore(plan): close SA-001')
        lines = self.boot()
        self.assertIn('PLAN: 0 open, 1 done', lines)
        self.assertTrue(any(line.startswith('RECENT: SA-001 by m') for line in lines))
        self.assertIn('SA-002', plan.new_task(self.root, 'next')[1][0])

    def test_validate_flags_untyped_acceptance_and_missing_owner(self):
        self.init_plan()
        task = self.root / '.store-automation/tasks/SA-001.md'
        task.write_text(READY_TASK.format(id='SA-001').replace('[machine] ', '').replace(
            'Status: READY', 'Status: IN_PROGRESS'), encoding='utf-8')
        code, lines = plan.validate(self.root)
        self.assertEqual(code, 2)
        self.assertTrue(any('kind tag' in line for line in lines))
        self.assertTrue(any('without Owner' in line for line in lines))

    def test_start_needs_done_dependencies_and_a_strong_ready_check_for_risk(self):
        """B12/B13: `start` itself enforces what boot only suggested."""
        self.init_plan()
        tasks = self.root / '.store-automation/tasks'
        (tasks / 'SA-002.md').write_text(READY_TASK.format(id='SA-002').replace('Depends: -', 'Depends: SA-999'),
                                         encoding='utf-8')
        code, lines = plan.start(self.root, 'SA-002', 'm')
        self.assertEqual(code, 2)
        self.assertIn('SA-999', lines[0])
        (tasks / 'SA-003.md').write_text(READY_TASK.format(id='SA-003').replace('Risk: LOW', 'Risk: MEDIUM'),
                                         encoding='utf-8')
        code, lines = plan.start(self.root, 'SA-003', 'm')
        self.assertIn('ready by', lines[0])
        self.assertTrue(any('ready by' in line for line in plan.validate(self.root)[1]))
        plan.append_section(tasks / 'SA-003.md', 'Notes', '- ready by opus: risk and contract confirmed')
        self.assertEqual(plan.start(self.root, 'SA-003', 'm')[0], 0)
        self.assertIn('- start by m | risk=MEDIUM | contract=', (tasks / 'SA-003.md').read_text(encoding='utf-8'))

    def test_parallel_starts_leave_exactly_one_writer(self):
        """B06: the read-check-write of `start` is atomic per checkout."""
        self.init_plan()
        tasks = self.root / '.store-automation/tasks'
        for n in range(2, 7):
            (tasks / f'SA-00{n}.md').write_text(READY_TASK.format(id=f'SA-00{n}'), encoding='utf-8')
        store = Path(__file__).resolve().parents[1] / 'store.py'
        procs = [subprocess.Popen([sys.executable, str(store), '--project', str(self.root), 'start', f'SA-00{n}',
                                   '--owner', f'agent{n}'], stdout=subprocess.PIPE, text=True) for n in range(1, 7)]
        started = sum('STARTED' in p.communicate()[0] for p in procs)
        owners = [t['owner'] for t in plan.list_tasks(self.root) if t['status'] == 'IN_PROGRESS']
        self.assertEqual((started, len(owners)), (1, 1))
        self.assertTrue(owners[0])

    def test_blocked_review_asks_for_a_fix_and_clean_in_progress_resumes(self):
        """M11 and m8."""
        self.init_plan()
        task = self.root / '.store-automation/tasks/SA-001.md'
        plan.start(self.root, 'SA-001', 'small')
        self.assertEqual(self.boot()[0], 'STATE: RESUME')  # clean tree: nothing was interrupted mid-edit
        plan.set_header(task, 'Status', 'REVIEW')
        plan.append_section(task, 'Review', '- review by strong | BLOCKED | digest=abc | contract=def')
        lines = self.boot()
        self.assertTrue(any(line.startswith('FIX: SA-001') for line in lines), lines)
        self.assertFalse(any(line.startswith('REVIEW:') for line in lines))

    def test_ids_are_unique_across_branches_and_headers_keep_crlf(self):
        """M9 and m15."""
        self.init_plan()
        git(self.root, 'switch', '-qc', 'feature')
        plan.new_task(self.root, 'on feature')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'docs(plan): feature task')
        git(self.root, 'switch', '-q', 'main')
        self.assertIn('SA-003', plan.new_task(self.root, 'on main')[1][0])
        task = self.root / '.store-automation/tasks/SA-001.md'
        task.write_bytes(task.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        plan.set_header(task, 'Owner', 'x')
        plan.append_section(task, 'Notes', '- note')
        self.assertNotIn(b'\n', task.read_bytes().replace(b'\r\n', b''))

    def test_glob_double_star_matches_root_files(self):
        self.assertTrue(plan.matches('app.py', '**/*.py'))
        self.assertTrue(plan.matches('src/a/app.py', '**/*.py'))
        self.assertFalse(plan.matches('app.js', '**/*.py'))

    def test_validate_warns_on_underrated_risk_and_unprobed_assumption(self):
        self.init_plan()
        task = self.root / '.store-automation/tasks/SA-001.md'
        task.write_text(READY_TASK.format(id='SA-001').replace('"selam desin"', 'login session persistence'),
                        encoding='utf-8')
        product = self.root / '.store-automation/product.md'
        product.write_text(product.read_text(encoding='utf-8').replace(
            '- RA-1: <', '- RA-1: offline sync works <'), encoding='utf-8')
        lines = plan.validate(self.root)[1]
        self.assertTrue(any('but Risk is LOW' in line for line in lines), lines)
        self.assertTrue(any('RA-1' in line and 'probed by no task' in line for line in lines), lines)

    def test_boot_flags_a_commit_that_differs_from_the_accepted_bytes(self):
        """m10: a pre-commit hook (or a forgotten file) changes what DONE verified; boot says so."""
        from runtime import accept
        self.init_plan()
        task = self.root / '.store-automation/tasks/SA-001.md'
        plan.start(self.root, 'SA-001', 'm')
        task.write_text(task.read_text(encoding='utf-8').replace('- [ ] [', '- [x] [').replace(
            '`python -m', f'`{sys.executable.replace(chr(92), "/")} -m'), encoding='utf-8')
        accept.check(self.root, 'SA-001', actor='m')
        trailers = accept.accept(self.root, 'SA-001', 'm')[1]
        message = 'feat: greet\n\n' + '\n'.join(t.strip() for t in trailers if t.startswith('  SA-'))
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', message)
        self.assertFalse(any('differ from what `accept` verified' in line for line in self.boot()))
        (self.root / 'app.py').write_text('def greet():\n    return "selam"  # hook\n')  # what a formatter does
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '--amend', '-m', message)
        self.assertTrue(any('differ from what `accept` verified' in line for line in self.boot()))

    def test_adr_shape_is_checked_and_plan_never_imports_legacy(self):
        self.init_plan()
        (self.root / '.store-automation/decisions/ADR-001.md').write_text('# ADR-001\nStatus: PROPOSED\n## Context\n')
        self.assertTrue(any('ADR-001.md: missing Status' in line for line in plan.validate(self.root)[1]))
        code = 'import sys, runtime.plan; sys.exit("runtime.legacy" in sys.modules)'
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(subprocess.run([sys.executable, '-c', code], cwd=root).returncode, 0)

    def test_no_git_folder_degrades_but_works(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan.init(root)
            self.assertEqual(plan.boot(root)[1][0], 'STATE: NO_GIT')


if __name__ == '__main__':
    unittest.main()
