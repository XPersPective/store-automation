"""Validate scoped delivery records, not the truth of self-reported observations.

The caller supplies host-owned assignments and source-bound observations. Files,
native sessions and trust are checked at the receipt boundary, never inferred
from an agent's PASS string. No Brain, provider, shell or network dependency.
"""
import hashlib
import json
import math


STATES = {'PREPARED', 'RUNNING', 'COMPLETED', 'BLOCKED', 'FAILED',
          'INTERRUPTED', 'UNVERIFIED'}
KINDS = {'machine', 'interaction', 'visual', 'accessibility', 'security',
         'integration', 'artifact', 'remote', 'user_feedback'}


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be nonempty text')
    return value


def strings(value, label, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(label + ' must be a list')
    for item in value:
        text(item, label)
    if len(value) != len(set(value)):
        raise ValueError(label + ' contains duplicates')
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def validate_task(task):
    if not isinstance(task, dict):
        raise ValueError('Task must be an object')
    for key in ('id', 'project', 'objective', 'acceptance_scope'):
        text(task.get(key), key)
    strings(task.get('scope'), 'scope', True)
    strings(task.get('out_of_scope'), 'out_of_scope')
    if text(task.get('risk'), 'risk') not in ('LOW', 'MEDIUM', 'HIGH'):
        raise ValueError('Unknown risk')
    permissions = task.get('permissions')
    if (not isinstance(permissions, dict) or
            permissions.get('paid_api') is not False or
            permissions.get('production') is not False or
            type(permissions.get('write')) is not bool):
        raise ValueError('Explicit write and no paid API/production permissions required')
    if type(task.get('independent_review')) is not bool:
        raise ValueError('Explicit independent_review boolean required')
    if task['risk'] != 'LOW' and not task['independent_review']:
        raise ValueError('Non-low-risk work requires independent review')
    criteria = task.get('criteria')
    if not isinstance(criteria, list) or not criteria:
        raise ValueError('Criteria required')
    ids = []
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError('Criterion must be an object')
        ids.append(text(criterion.get('id'), 'criterion id'))
        text(criterion.get('description'), 'criterion description')
        if type(criterion.get('required')) is not bool:
            raise ValueError('Explicit required boolean required')
        kinds = strings(criterion.get('kinds'), 'criterion kinds', True)
        if not set(kinds) <= KINDS:
            raise ValueError('Unknown evidence kind')
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate criterion')
    return task


def validate_report(report, assignment):
    """Structural/identity validation; transport success is not acceptance."""
    if not isinstance(report, dict) or not isinstance(assignment, dict):
        raise ValueError('Report and assignment must be objects')
    for key in ('task', 'project', 'attempt', 'role'):
        text(assignment.get(key), key)
        if report.get(key) != assignment[key]:
            raise ValueError('Report differs from assigned ' + key)
    for key in ('provider', 'model', 'effort'):
        actual = assignment.get(key)
        if actual is not None:
            text(actual, key)
        if report.get(key) != actual:
            raise ValueError('Report differs from actual ' + key)
    if text(report.get('state'), 'report state') not in STATES:
        raise ValueError('Unknown report state')
    for key in ('changed_files', 'evidence', 'blockers'):
        strings(report.get(key), key)
    text(report.get('next_action'), 'next_action')
    if report['state'] == 'COMPLETED' and report['blockers']:
        raise ValueError('COMPLETED report has blockers')
    usage = report.get('usage')
    if usage is not None:
        if not isinstance(usage, dict):
            raise ValueError('Usage must be null or an object')
        for key, value in usage.items():
            text(key, 'usage key')
            if value is not None and (type(value) not in (float, int) or
                                      not math.isfinite(value) or value < 0):
                raise ValueError('Invalid measured usage')
    return report


def evaluate_acceptance(task, observations, review=None, *, subject,
                        implementation, reviewer=None):
    """Evaluate one explicit final-output subject with caller-owned receipts.

This function validates recorded evidence only. A receipt boundary must verify
the subject and referenced bytes and establish the observer's provenance.
Superseded observations must be excluded explicitly by that boundary.
"""
    validate_task(task)
    text(subject, 'final-output subject')
    if not isinstance(observations, list) or not isinstance(implementation, dict):
        raise ValueError('Observation list and implementation receipt required')
    required_hash = fingerprint(task)
    problems, missing = [], []
    for key, expected in (('task', task['id']), ('project', task['project']),
                          ('task_hash', required_hash), ('output_subject', subject)):
        if implementation.get(key) != expected:
            problems.append('Implementation mismatch: ' + key)
    text(implementation.get('input_subject'), 'implementation input subject')
    if not task['permissions']['write'] and implementation['input_subject'] != subject:
        problems.append('Read-only implementation changed its source')
    text(implementation.get('attempt'), 'implementation attempt')
    text(implementation.get('actor'), 'implementation actor')
    if implementation.get('state') != 'COMPLETED':
        missing.append('Implementation has no completed receipt')
    if implementation.get('provenance') != 'verified':
        missing.append('Implementation provenance unverified')
    criteria = {c['id']: c for c in task['criteria']}
    by_criterion = {key: [] for key in criteria}
    ids = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError('Observation must be an object')
        identity = text(observation.get('id'), 'observation id')
        if identity in ids:
            raise ValueError('Duplicate observation')
        ids.add(identity)
        criterion = text(observation.get('criterion'), 'observation criterion')
        kind = text(observation.get('kind'), 'observation kind')
        if criterion not in criteria or kind not in KINDS:
            raise ValueError('Unknown observation criterion/kind')
        if text(observation.get('result'), 'observation result') not in ('PASS', 'FAIL', 'UNVERIFIED', 'NOT_APPLICABLE'):
            raise ValueError('Unknown observation result')
        for key in ('reference', 'observer', 'method', 'environment', 'captured_at'):
            text(observation.get(key), 'observation ' + key)
        if any(observation.get(key) != expected for key, expected in
               (('task', task['id']), ('project', task['project']),
                ('task_hash', required_hash), ('subject', subject))):
            problems.append('Stale or foreign observation: ' + identity)
            continue
        if observation.get('result') == 'FAIL':
            problems.append('Failed observation: ' + identity)
        if observation.get('provenance') != 'verified':
            missing.append('Observation provenance unverified: ' + identity)
            continue
        if observation['result'] == 'NOT_APPLICABLE':
            text(observation.get('reason'), 'N/A reason')
            if criteria[criterion]['required']:
                problems.append('Required criterion cannot be N/A: ' + criterion)
        by_criterion[criterion].append(observation)
    results = {}
    for identity, criterion in criteria.items():
        passed = {o['kind'] for o in by_criterion[identity] if o['result'] == 'PASS'}
        absent = sorted(set(criterion['kinds']) - passed)
        results[identity] = {'satisfied': not absent, 'missing_kinds': absent,
                             'observations': [o['id'] for o in by_criterion[identity]]}
        if absent and criterion['required']:
            missing.append('Missing evidence: ' + identity + '/' + ','.join(absent))
    if task['independent_review'] and (review is None or reviewer is None):
        missing.append('Independent review missing')
    if review is not None:
        if not isinstance(review, dict) or not isinstance(reviewer, dict):
            raise ValueError('Review requires caller-owned reviewer receipt')
        for key, expected in (('task', task['id']), ('project', task['project']),
                              ('task_hash', required_hash), ('subject', subject)):
            if review.get(key) != expected:
                problems.append('Review mismatch: ' + key)
        text(reviewer.get('attempt'), 'reviewer attempt')
        text(reviewer.get('actor'), 'reviewer actor')
        if (reviewer['attempt'] == implementation['attempt'] or
                reviewer['actor'] == implementation['actor']):
            problems.append('Reviewer is not independent')
        for key, expected in (('task', task['id']), ('project', task['project']),
                              ('task_hash', required_hash), ('input_subject', subject), ('output_subject', subject),
                              ('state', 'COMPLETED'), ('role', 'reviewer')):
            if reviewer.get(key) != expected:
                problems.append('Reviewer receipt mismatch: ' + key)
        if review.get('attempt') != reviewer['attempt']:
            problems.append('Review has no matching assignment')
        if reviewer.get('provenance') != 'verified':
            missing.append('Reviewer provenance unverified')
        covered = strings(review.get('criteria'), 'reviewed criteria')
        if not set(criteria) >= set(covered):
            raise ValueError('Review names unknown criterion')
        if not {c['id'] for c in task['criteria'] if c['required']} <= set(covered):
            missing.append('Review does not cover required criteria')
        if text(review.get('verdict'), 'review verdict') not in ('PASS', 'BLOCKED', 'UNVERIFIED'):
            raise ValueError('Unknown review verdict')
        if review['verdict'] == 'BLOCKED':
            problems.append('Review blocked')
        elif review['verdict'] != 'PASS':
            missing.append('Review unverified')
        findings = review.get('findings')
        if not isinstance(findings, list):
            raise ValueError('Findings must be a list')
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValueError('Finding must be an object')
            text(finding.get('description'), 'finding description')
            if text(finding.get('severity'), 'finding severity') not in ('BLOCKER', 'MAJOR', 'MINOR'):
                raise ValueError('Unknown finding severity')
            violations = strings(finding.get('violates'), 'finding violations')
            if not set(violations) <= set(criteria):
                raise ValueError('Finding names unknown criterion')
            # Fixed findings belong in history; a fresh review must establish the fix.
            if (finding['severity'] != 'MINOR' or violations or
                    finding.get('disposition') != 'accepted' or
                    not isinstance(finding.get('reason'), str) or not finding['reason'].strip() or
                    not isinstance(finding.get('decision_owner'), str) or not finding['decision_owner'].strip()):
                problems.append('Unresolved finding: ' + finding['description'])
    return {'status': 'BLOCKED' if problems else 'UNVERIFIED' if missing else 'ACCEPTED',
            'scope': task['acceptance_scope'], 'task': task['id'], 'subject': subject,
            'criteria': results, 'problems': problems, 'missing': missing,
            'claim': 'Recorded evidence only; receipt provenance and current bytes required'}
