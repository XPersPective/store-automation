"""File-backed acceptance with an explicit trusted supervisor boundary.

Attestations come from the coordinating host, NEVER from worker output.
This is an audit trail, not authentication against the same OS user. Hosts
without observable native results leave the evidence UNVERIFIED.
"""
from pathlib import Path
from .acceptance import evaluate_acceptance, fingerprint, text, validate_report
from .receipts import read_record, verify_snapshot, append_record


def gate(root, bundle, attestations):
    task = bundle['task']
    if Path(task['project']).resolve() != Path(root).resolve():
        raise ValueError('Foreign project')
    subject = verify_snapshot(root, bundle['source'])
    if not isinstance(attestations, list):
        raise ValueError('Supervisor attestations must be a list')
    trusted = {}
    for att in attestations:
        key = fingerprint(att['record'])
        if key in trusted:
            raise ValueError('Duplicate attestation')
        for field in ('observer', 'method', 'native_reference', 'observed_at'):
            text(att.get(field), 'attestation ' + field)
        # Resolve all references even when the bundle does not consume one.
        read_record(root, att['record'])
        trusted[key] = att

    def resolve(ref, outcome=False):
        record = read_record(root, ref)
        record['provenance'] = 'unverified'
        att = trusted.get(fingerprint(ref))
        if att:
            if outcome:
                if (att.get('actor') != record.get('actor') or
                        att.get('state') != record.get('state') or
                        att['native_reference'] != record.get('native_reference') or
                        att['observer'] == record.get('actor')):
                    raise ValueError('Native outcome attestation mismatch')
            record['provenance'] = 'verified'
        return record

    def outcome(ref):
        record = resolve(ref, True)
        assignment = read_record(root, record['assignment'])
        if assignment['task_snapshot'] != task or assignment['task_hash'] != fingerprint(task):
            raise ValueError('Outcome belongs to another task version')
        validate_report(record['report'], assignment)
        if record['report']['state'] != record['state']:
            raise ValueError('Outcome state differs from report')
        for key in ('task', 'project', 'task_hash', 'attempt', 'role', 'actor',
                    'provider', 'model', 'effort', 'input_subject'):
            if record.get(key) != assignment.get(key):
                raise ValueError('Outcome differs from assignment: ' + key)
        if record['output_subject'] != verify_snapshot(root, record['output_snapshot']):
            raise ValueError('Output snapshot mismatch')
        return record

    implementation = outcome(bundle['implementation'])
    observations = []
    for ref in bundle['observations']:
        obs = resolve(ref)
        evidence = read_record(root, obs['evidence'])
        if obs['kind'] == 'machine':
            if (evidence.get('state') != 'PASS' or evidence.get('source_stable') is not True or
                    evidence.get('exit_code') != 0 or
                    Path(text(evidence.get('cwd'), 'check project')).resolve() != Path(root).resolve() or
                    verify_snapshot(root, evidence['input_snapshot']) != subject):
                raise ValueError('Machine evidence does not establish current success')
        observations.append(obs)
    reviewer = outcome(bundle['reviewer']) if bundle.get('reviewer') else None
    review = resolve(bundle['review']) if bundle.get('review') else None
    if review is not None and review['provenance'] != 'verified':
        review['verdict'] = 'UNVERIFIED'
    result = evaluate_acceptance(task, observations, review, subject=subject,
                                implementation=implementation, reviewer=reviewer)
    result['trust_boundary'] = 'Supervisor inspected native tools; local files are not host authentication'
    result['receipt'] = append_record(root, 'acceptance', dict(
        result=result.copy(), bundle=bundle, attestations=attestations))
    return result
