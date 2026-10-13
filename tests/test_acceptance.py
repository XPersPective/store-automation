import copy
import unittest

from runtime.acceptance import evaluate_acceptance, fingerprint, validate_report, validate_task


def example():
    task = dict(id='save-item', project='selected-project', objective='Save and reopen item',
                acceptance_scope='Item persistence in test environment', scope=['app.py'],
                out_of_scope=['production'], risk='MEDIUM', independent_review=True,
                permissions=dict(write=True, paid_api=False, production=False),
                criteria=[dict(id='save', description='Item survives reopen', required=True,
                               kinds=['integration'])])
    common = dict(task=task['id'], project=task['project'], task_hash=fingerprint(task))
    implementation = dict(**common, attempt='impl-1', actor='worker-1',
                          input_subject='before-edit', output_subject='after-edit',
                          state='COMPLETED', provenance='verified')
    observations = [dict(**common, id='obs-1', criterion='save', kind='integration',
                         result='PASS', subject='after-edit', reference='run/save.json',
                         observer='test-runner', method='write then reopen database',
                         environment='temporary local project', captured_at='2026-10-13T12:00:00Z',
                         provenance='verified')]
    reviewer = dict(**common, attempt='review-1', actor='reviewer-1', role='reviewer',
                    state='COMPLETED', input_subject='after-edit', output_subject='after-edit', provenance='verified')
    review = dict(**common, attempt='review-1', subject='after-edit', criteria=['save'],
                  verdict='PASS', findings=[])
    return task, observations, review, implementation, reviewer


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.task, self.obs, self.review, self.impl, self.reviewer = example()

    def evaluate(self):
        return evaluate_acceptance(self.task, self.obs, self.review, subject='after-edit',
                                   implementation=self.impl, reviewer=self.reviewer)

    def test_plain_task_without_brain_and_authorized_edit_accepts_final_output(self):
        validate_task(self.task)
        result = self.evaluate()
        self.assertEqual(result['status'], 'ACCEPTED')
        self.assertEqual(result['scope'], self.task['acceptance_scope'])
        self.assertNotEqual(self.impl['input_subject'], self.impl['output_subject'])

    def test_report_rejects_original_invalid_state_role_and_identity_bugs(self):
        assignment = dict(task='save-item', project='selected-project', attempt='impl-1',
                          role='implementer', provider='host', model=None, effort=None)
        report = dict(**assignment, state='COMPLETED', changed_files=['app.py'],
                      evidence=['run/save.json'], blockers=[], next_action='Review', usage=None)
        validate_report(report, assignment)
        for key, value in [('state', 'BANANA'), ('state', ''), ('role', 'unassigned'),
                           ('task', 'other'), ('project', 'foreign'), ('attempt', 'other'),
                           ('model', 'invented'), ('state', []), ('blockers', ['not actually complete']),
                           ('usage', {'tokens': True}), ('usage', {'tokens': float('nan')})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_report(dict(report, **{key: value}), assignment)

    def test_transport_completion_and_missing_journey_do_not_accept(self):
        self.obs = []
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')
        self.assertIn('Missing evidence: save/integration', self.evaluate()['missing'])

    def test_machine_check_does_not_substitute_for_integration(self):
        self.obs[0]['kind'] = 'machine'
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')

    def test_foreign_stale_or_failed_observation_blocks(self):
        original = copy.deepcopy(self.obs)
        for key, value in [('project', 'foreign'), ('subject', 'before-edit'),
                           ('task_hash', 'old'), ('task', 'other'), ('result', 'FAIL')]:
            self.obs = copy.deepcopy(original)
            self.obs[0][key] = value
            with self.subTest(key=key):
                self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_unverified_provenance_and_missing_review_stay_unknown(self):
        self.obs[0]['provenance'] = 'declared'
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')
        self.obs[0]['provenance'] = 'verified'
        self.review = None
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')

    def test_required_criterion_cannot_be_waived_as_na(self):
        self.obs[0].update(result='NOT_APPLICABLE', reason='Convenient to skip')
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_review_identity_ownership_and_independence(self):
        original = self.reviewer.copy()
        for key, value in [('attempt', 'impl-1'), ('actor', 'worker-1'),
                           ('project', 'foreign'), ('input_subject', 'old'),
                           ('task_hash', 'old'), ('output_subject', 'changed'), ('role', 'implementer')]:
            self.reviewer = dict(original, **{key: value})
            with self.subTest(key=key):
                self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        self.reviewer = dict(original, provenance='declared')
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')

    def test_minor_finding_retained_only_without_acceptance_violation(self):
        finding = dict(description='Optional export is absent', severity='MINOR',
                       violates=[], disposition='accepted', reason='Outside confirmed scope',
                       decision_owner='product-coordinator')
        self.review['findings'] = [finding]
        self.assertEqual(self.evaluate()['status'], 'ACCEPTED')
        self.assertEqual(len(self.review['findings']), 1)
        for change in [dict(severity='BLOCKER'), dict(violates=['save']),
                       dict(disposition='deferred'), dict(reason=''), dict(decision_owner='')]:
            self.review['findings'] = [dict(finding, **change)]
            self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_readonly_implementation_cannot_change_input(self):
        self.task['permissions']['write'] = False
        for record in [self.impl, self.reviewer, self.review, *self.obs]:
            record['task_hash'] = fingerprint(self.task)
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        self.impl['input_subject'] = 'after-edit'
        self.assertEqual(self.evaluate()['status'], 'ACCEPTED')

    def test_malformed_json_values_raise_validation_errors(self):
        for field in ('criterion', 'kind', 'result'):
            original = self.obs[0][field]
            self.obs[0][field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.evaluate()
            self.obs[0][field] = original

    def test_missing_coverage_and_invalid_types_fail_closed(self):
        self.review['criteria'] = []
        self.assertEqual(self.evaluate()['status'], 'UNVERIFIED')
        for change in [dict(risk='banana'), dict(independent_review=False),
                       dict(criteria=[]), dict(scope='app.py')]:
            with self.assertRaises(ValueError):
                validate_task(dict(self.task, **change))
        self.obs.append(copy.deepcopy(self.obs[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate observation'):
            self.evaluate()


if __name__ == '__main__':
    unittest.main()
