import os
import sys
import unittest

from runtime import accept, plan
from test_plan import READY_TASK, Repo, git


class AcceptTests(Repo):
    def setUp(self):
        super().setUp()
        self.init_plan()
        self.task = self.root / '.store-automation/tasks/SA-001.md'
        # The interpreter running the tests, so Verify works without PATH assumptions.
        self.task.write_text(READY_TASK.format(id='SA-001').replace(
            '`python -m unittest test_app`', f'`{sys.executable.replace(chr(92), "/")} -m unittest test_app`'),
            encoding='utf-8')
        plan.start(self.root, 'SA-001', 'small-model')
        self.me = 'small-model'

    def edit(self, old, new):
        self.task.write_text(self.task.read_text(encoding='utf-8').replace(old, new), encoding='utf-8')

    def tick(self):
        self.edit('- [ ] [', '- [x] [')

    def status(self):
        return plan.parse_task(self.task)['status']

    def items(self):
        return plan.parse_task(self.task)['items']

    def test_low_risk_done_only_with_current_passing_check(self):
        self.tick()
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(any('no check on current source' in line for line in lines))
        self.assertEqual(accept.check(self.root, 'SA-001', actor=self.me)[0], 0)
        (self.root / 'app.py').write_text('def greet():\n    return "selam"  # edited after check\n')
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 1)
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 0, lines)
        self.assertEqual(self.status(), 'DONE')
        self.assertIn('  SA-Verification: local', lines)

    def test_failing_check_blocks_and_unticked_item_stays_unverified(self):
        accept.check(self.root, 'SA-001', actor=self.me)
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 1)
        (self.root / 'app.py').write_text('def greet():\n    return "wrong"\n')
        self.assertEqual(accept.check(self.root, 'SA-001', actor=self.me)[0], 1)
        self.tick()
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 2)
        self.assertTrue(any('latest check failed' in line for line in lines))

    def test_hand_written_pass_is_refused(self):
        """M1: a PASS line typed by hand, or copied onto a real failing log, is not evidence."""
        (self.root / 'app.py').write_text('def greet():\n    return "wrong"\n')
        accept.check(self.root, 'SA-001', actor=self.me)
        self.tick()
        real = plan.parse_task(self.task)['evidence'][-1]
        self.assertIn('| FAIL |', real)
        plan.append_section(self.task, 'Evidence', real.replace('| FAIL | exit=1', '| PASS | exit=0'))
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 2, lines)
        self.assertTrue(any('does not match its log' in line for line in lines))
        plan.append_section(self.task, 'Evidence', real.replace('| FAIL | exit=1', '| PASS | exit=0').replace(
            '.log@', '-typed.log@'))
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 1)  # no such log: rerun `check`

    def test_medium_risk_waits_for_a_different_reviewer_on_current_source(self):
        self.edit('Risk: LOW', 'Risk: MEDIUM')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith('REVIEW_PENDING'))
        self.assertEqual(self.status(), 'REVIEW')
        self.assertEqual(accept.review(self.root, 'SA-001', 'small-model', 'PASS')[0], 2)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS', ['MAJOR: greet ignores locale'])
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS', ['QUALITY: copy is bland | accepted: ok | owner: user',
                                                                     'MINOR: docstring missing | accepted: cosmetic | owner: user'])
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 0, lines)
        self.assertIn('  SA-Reviewer: strong-model', lines)

    def test_quality_gap_blocks_unless_the_user_accepts_it(self):
        self.edit('Risk: LOW', 'Risk: MEDIUM')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS', ['QUALITY: raw "Failed to fetch" shown to users'])
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        with self.assertRaisesRegex(ValueError, 'user only'):
            accept.review(self.root, 'SA-001', 'strong-model', 'PASS', ['QUALITY: x | accepted: later | owner: SA-001'])

    def test_lowered_risk_and_changed_spec_need_new_evidence_and_review(self):
        """M2/B03: Risk lowered after start keeps its review; a reworded Acceptance voids old check and review."""
        self.edit('Risk: LOW', 'Risk: HIGH')
        self.edit('## Notes\n', '## Notes\n- ready by strong-model: risk HIGH, spec complete\n')
        plan.set_header(self.task, 'Status', 'READY')
        self.assertEqual(plan.start(self.root, 'SA-001', self.me)[0], 0)
        self.edit('Risk: HIGH', 'Risk: LOW')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual((code, lines[0][:14]), (1, 'REVIEW_PENDING'), lines)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS')
        self.edit('asserted by test_app.py', 'and authorization asserted by test_app.py')
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1, lines)
        self.assertTrue(any('no check on current source and spec' in line for line in lines))
        accept.check(self.root, 'SA-001', actor=self.me)
        self.assertTrue(accept.accept(self.root, 'SA-001', self.me)[1][0].startswith('REVIEW_PENDING'))
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS')
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 0, lines)
        self.assertIn('  SA-Verification: global', lines)

    def test_each_criterion_needs_its_own_observation_and_visual_needs_a_render(self):
        """B10/M4: a desktop screenshot does not prove the 320px item; a note alone is not visual evidence."""
        self.edit('## Verify', '- [ ] [visual] greeting visible at 1280px\n- [ ] [visual] greeting visible at 320px\n'
                  '\n## Verify')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        wide, narrow = [i['id'] for i in self.items() if i['kind'] == 'visual']
        (self.root / 'shot.png').write_bytes(b'seen')
        with self.assertRaisesRegex(ValueError, '--criterion'):
            accept.evidence(self.root, 'SA-001', 'visual', 'home screen', ['shot.png'], self.me)
        with self.assertRaisesRegex(ValueError, 'rendered result'):
            accept.evidence(self.root, 'SA-001', 'visual', 'looked fine', (), self.me, [wide])
        accept.evidence(self.root, 'SA-001', 'visual', 'home at 1280px', ['shot.png'], self.me, [wide])
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(any(narrow in line for line in lines))
        accept.evidence(self.root, 'SA-001', 'visual', 'home at 320px', ['shot.png'], self.me, [narrow])
        (self.root / 'shot.png').write_bytes(b'edited')
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        with self.assertRaises(ValueError):
            accept.evidence(self.root, 'SA-001', 'machine', 'hand-written PASS', (), self.me)

    def test_waiting_for_user_frees_the_queue_and_the_implementer_cannot_review(self):
        self.edit('## Verify', '- [ ] [user_feedback] user picked option a or b\n\n## Verify')
        self.edit('- [ ] [machine]', '- [x] [machine]')
        self.edit('Risk: LOW', 'Risk: MEDIUM')
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith('WAITING_USER'))
        self.assertEqual((self.status(), plan.parse_task(self.task)['owner']), ('BLOCKED', ''))
        self.assertTrue(any(line.startswith('QUESTIONS') for line in plan.boot(self.root)[1]))
        self.edit('## Notes\n', '## Notes\n- ready by strong-model: user answered\n')
        self.assertEqual(plan.start(self.root, 'SA-001', 'next-model')[0], 0)
        accept.evidence(self.root, 'SA-001', 'user_feedback', 'user chose a on 2026-10-14', (), 'next-model')
        self.tick()
        accept.accept(self.root, 'SA-001', 'next-model')
        # M3: small-model implemented before the wait, so it is not an independent reviewer now.
        code, lines = accept.review(self.root, 'SA-001', 'small-model', 'PASS')
        self.assertEqual(code, 2, lines)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS')
        self.assertEqual(accept.accept(self.root, 'SA-001', 'next-model')[0], 0)

    def test_non_owner_cannot_act_without_takeover(self):
        with self.assertRaisesRegex(ValueError, 'takeover'):
            accept.check(self.root, 'SA-001', actor='other-model')
        with self.assertRaisesRegex(ValueError, '--as'):
            accept.accept(self.root, 'SA-001', '')

    def test_reviewer_cannot_own_an_accepted_exception(self):
        with self.assertRaisesRegex(ValueError, 'owner must be'):
            accept.review(self.root, 'SA-001', 'strong-model', 'PASS',
                          ['MINOR: naming | accepted: fine | owner: strong-model'])

    def test_unresolved_or_malformed_external_and_empty_verify_prevent_done(self):
        """B04: what validate rejects, accept rejects too."""
        plan.append_section(self.task, 'External', '- upload aab | response_unknown | readback: track list')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(any('readback first' in line for line in lines))
        self.edit('response_unknown', 'response_lost')
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        self.edit('response_lost', 'confirmed')
        self.edit('test_app`\n', 'test_app\n')  # the backticks go: no Verify command remains
        self.edit('- `' + sys.executable.replace(chr(92), '/'), '- ' + sys.executable.replace(chr(92), '/'))
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 2, lines)
        self.assertTrue(any('Verify' in line for line in lines))

    def test_line_endings_do_not_change_the_digest(self):
        """M10: the same commit under another core.autocrlf keeps its evidence."""
        (self.root / 'app.py').write_bytes(b'def greet():\n    return "selam"\n')
        before, _ = accept.digest(self.root, ['app.py'])
        (self.root / 'app.py').write_bytes(b'def greet():\r\n    return "selam"\r\n')
        self.assertEqual(accept.digest(self.root, ['app.py'])[0], before)

    @unittest.skipUnless(os.name == 'nt', 'directory junctions are a Windows feature')
    def test_linked_path_in_areas_is_refused(self):
        """B07: a junction inside Areas must not let the digest read outside the project."""
        import _winapi
        import tempfile
        outside = tempfile.mkdtemp()
        self.addCleanup(lambda: os.path.isdir(outside) and __import__('shutil').rmtree(outside))
        (__import__('pathlib').Path(outside) / 'secret.txt').write_text('outside')
        _winapi.CreateJunction(outside, str(self.root / 'linked'))
        self.addCleanup(lambda: os.rmdir(self.root / 'linked'))
        with self.assertRaisesRegex(ValueError, 'Linked|no files|escapes'):
            accept.digest(self.root, ['linked/**'])

    def test_runs_stay_bounded_but_cited_logs_survive(self):
        """runs/ is pruned by age and count; a log an open task cites is never deleted."""
        accept.check(self.root, 'SA-001', actor=self.me)
        cited = plan.pdir(self.root) / accept.CHECK_RE.match(plan.parse_task(self.task)['evidence'][-1])['log']
        runs = plan.pdir(self.root) / 'runs'
        old = runs / 'SA-000-old.log'
        old.write_text('x')
        os.utime(old, (0, 0))
        os.utime(cited, (0, 0))
        for n in range(accept.RUNS_KEEP_FILES + 5):
            (runs / f'SA-000-{n:04d}.log').write_text('x')
        accept.prune_runs(self.root)
        self.assertFalse(old.exists())
        self.assertTrue(cited.is_file())
        self.assertLessEqual(len(list(runs.glob('*.log'))), accept.RUNS_KEEP_FILES + 1)

    def test_interaction_needs_a_recording_or_the_steps_and_ids_are_plain(self):
        self.edit('## Verify', '- [ ] [interaction] submit keeps input on error\n\n## Verify')
        with self.assertRaisesRegex(ValueError, 'step -> step'):
            accept.evidence(self.root, 'SA-001', 'interaction', 'worked fine', (), self.me)
        accept.evidence(self.root, 'SA-001', 'interaction', 'stop server -> submit -> message shown, input kept',
                        (), self.me)
        for bad in ('', 'a|b', 'x\ny', ' ' * 3, 'z' * 81):
            with self.assertRaises(ValueError, msg=repr(bad)):
                plan.agent_id(bad, '--as')

    def test_logs_of_the_same_second_never_overwrite(self):
        first, _ = accept._log_path(self.root, 'SA-001', 1)
        second, _ = accept._log_path(self.root, 'SA-001', 1)
        self.assertNotEqual(first, second)


if __name__ == '__main__':
    unittest.main()
