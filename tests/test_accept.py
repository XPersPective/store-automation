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

    def tick(self):
        self.task.write_text(self.task.read_text(encoding='utf-8').replace('- [ ] [', '- [x] ['), encoding='utf-8')

    def status(self):
        return plan.parse_task(self.task)['status']

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

    def test_medium_risk_waits_for_a_different_reviewer_on_current_source(self):
        self.task.write_text(self.task.read_text(encoding='utf-8').replace('Risk: LOW', 'Risk: MEDIUM'),
                             encoding='utf-8')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith('REVIEW_PENDING'))
        self.assertEqual(self.status(), 'REVIEW')
        self.assertEqual(accept.review(self.root, 'SA-001', 'small-model', 'PASS')[0], 2)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS', ['MAJOR: greet ignores locale'])
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        accept.review(self.root, 'SA-001', 'strong-model', 'PASS',
                      ['MINOR: docstring missing | accepted: cosmetic | owner: user'])
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 0, lines)
        self.assertIn('  SA-Reviewer: strong-model', lines)

    def test_visual_evidence_binds_screenshot_and_source(self):
        self.task.write_text(self.task.read_text(encoding='utf-8').replace(
            '## Verify', '- [ ] [visual] greeting visible on the home screen\n\n## Verify'), encoding='utf-8')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 1)
        (self.root / 'shot.png').write_bytes(b'seen')
        accept.evidence(self.root, 'SA-001', 'visual', 'home screen shows selam', ['shot.png'], self.me)
        (self.root / 'shot.png').write_bytes(b'edited')
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 2)
        with self.assertRaises(ValueError):
            accept.evidence(self.root, 'SA-001', 'machine', 'hand-written PASS', (), self.me)

    def test_waiting_for_user_frees_the_queue_then_resumes(self):
        self.task.write_text(self.task.read_text(encoding='utf-8').replace(
            '## Verify', '- [ ] [user_feedback] user picked option a or b\n\n## Verify'), encoding='utf-8')
        self.task.write_text(self.task.read_text(encoding='utf-8').replace(
            '- [ ] [machine]', '- [x] [machine]'), encoding='utf-8')
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith('WAITING_USER'))
        self.assertEqual(self.status(), 'BLOCKED')
        self.assertTrue(any(line.startswith('QUESTIONS') for line in plan.boot(self.root)[1]))
        self.assertEqual(plan.start(self.root, 'SA-001', 'next-model')[0], 0)
        self.me = 'next-model'
        accept.evidence(self.root, 'SA-001', 'user_feedback', 'user chose a on 2026-10-14', (), self.me)
        self.tick()
        self.assertEqual(accept.accept(self.root, 'SA-001', self.me)[0], 0)

    def test_non_owner_cannot_act_without_takeover(self):
        with self.assertRaisesRegex(ValueError, 'takeover'):
            accept.check(self.root, 'SA-001', actor='other-model')
        with self.assertRaisesRegex(ValueError, '--as'):
            accept.accept(self.root, 'SA-001', '')

    def test_reviewer_cannot_own_an_accepted_exception(self):
        with self.assertRaisesRegex(ValueError, 'owner must be'):
            accept.review(self.root, 'SA-001', 'strong-model', 'PASS',
                          ['MINOR: naming | accepted: fine | owner: strong-model'])

    def test_unresolved_external_operation_prevents_done(self):
        plan.append_section(self.task, 'External', '- upload aab | response_unknown | readback: track list')
        self.tick()
        accept.check(self.root, 'SA-001', actor=self.me)
        code, lines = accept.accept(self.root, 'SA-001', self.me)
        self.assertEqual(code, 1)
        self.assertTrue(any('readback first' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
