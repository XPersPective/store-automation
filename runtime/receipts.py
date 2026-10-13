"""Explicit public inputs and append-only evidence for native-host workflows.

No account files are read. Host outcomes are supervisor attestations, not a
cryptographic guarantee against another program running as the same OS user.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import uuid

from .acceptance import fingerprint, text, validate_report, validate_task


PRIVATE = re.compile(r'(^|/)(?:\.env(?:\.[^/]+)?|auth\.json|credentials?|secrets?|'
                     r'service-account[^/]*|key\.properties|id_rsa|id_ed25519)(/|$)|'
                     r'\.(?:jks|p8|p12|pfx|pem)$', re.I)
MAX_RECORD = 2_000_000


def public_path(root, name):
    """Check every ancestor before opening a file, including on Windows."""
    root = Path(root).absolute()
    text(name, 'relative path')
    parts = PureWindowsPath(name)
    if (parts.anchor or '\\' in name or '..' in parts.parts or ':' in name or
            any(part.endswith(('.', ' ')) or PureWindowsPath(part).is_reserved() for part in parts.parts) or
            PRIVATE.search(name) or any(ord(c) < 32 for c in name)):
        raise ValueError('Private or escaping path refused')
    path = root / name
    for entry in (path, *path.parents):
        if entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction()):
            raise ValueError('Linked path refused')
    if root.resolve() not in path.resolve().parents:
        raise ValueError('Path escapes project')
    return path


def snapshot(root, names):
    if (not isinstance(names, list) or not names or
            any(not isinstance(name, str) for name in names) or len(names) != len(set(names))):
        raise ValueError('Explicit distinct public input files required')
    paths = [(name, public_path(root, name)) for name in sorted(names)]
    # Validate the complete list before hashing any input.
    if any(not path.is_file() for _, path in paths):
        raise ValueError('Snapshot input missing or not a regular file')
    files = []
    for name, path in paths:
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        files.append({'path': name, 'sha256': digest})
    return {'files': files, 'subject': fingerprint(files)}


def verify_snapshot(root, recorded):
    if not isinstance(recorded, dict) or not isinstance(recorded.get('files'), list):
        raise ValueError('Snapshot record required')
    actual = snapshot(root, [entry['path'] for entry in recorded['files']])
    if actual != recorded:
        raise ValueError('Stale source or changed snapshot manifest')
    return actual['subject']


def append_record(root, category, value):
    if category not in ('assignment', 'outcome', 'observation', 'handoff', 'check', 'review', 'acceptance'):
        raise ValueError('Unknown record category')
    body = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    if len(body.encode()) > MAX_RECORD:
        raise ValueError('Record exceeds bound; reference public artifacts instead')
    relative = '.store-automation/runs/' + category + '-' + uuid.uuid4().hex + '.json'
    path = public_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(body + '\n')
        stream.flush()
        import os
        os.fsync(stream.fileno())
    return {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_record(root, reference):
    if not isinstance(reference, dict):
        raise ValueError('Hashed record reference required')
    path = public_path(root, reference.get('path'))
    if not path.is_file() or path.stat().st_size > MAX_RECORD:
        raise ValueError('Missing or oversized record')
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != reference.get('sha256'):
        raise ValueError('Changed record')
    return json.loads(body)


def prepare(root, task, role, actor, files, *, provider=None, model=None, effort=None,
            enforced_scope='unverified'):
    validate_task(task)
    text(role, 'role')
    text(actor, 'assigned actor')
    if Path(task['project']).resolve() != Path(root).resolve():
        raise ValueError('Task belongs to another project')
    inputs = snapshot(root, files)
    for value in (provider, model, effort):
        if value is not None:
            text(value, 'route value')
    record = dict(task=task['id'], project=task['project'], task_hash=fingerprint(task),
                  task_snapshot=task, attempt=uuid.uuid4().hex, role=role, actor=actor,
                  provider=provider, model=model, effort=effort, state='PREPARED',
                  requested_permissions=task['permissions'], enforced_scope=enforced_scope,
                  input_snapshot=inputs, input_subject=inputs['subject'],
                  created_at=datetime.now(timezone.utc).isoformat())
    return append_record(root, 'assignment', record)


def finish(root, assignment_ref, report, *, output_files, native_reference,
           observed_actor, observed_state, observer):
    """Supervisor records a tool-observed outcome; not a worker self-attestation.

The coordinator must actually inspect native_reference using that host. This
function cannot introspect every host or certify a caller-supplied transcript.
The returned provenance stays declared until the coordinator verifies it.
"""
    assignment = read_record(root, assignment_ref)
    validate_report(report, assignment)
    text(native_reference, 'native tool result reference')
    text(observer, 'supervisor observer')
    if observed_actor != assignment['actor'] or observer == observed_actor:
        raise ValueError('Outcome observer/actor mismatch')
    if observed_state != report['state']:
        raise ValueError('Report disagrees with observed native outcome')
    if not assignment['requested_permissions']['write'] or assignment['role'] == 'reviewer':
        verify_snapshot(root, assignment['input_snapshot'])
    output = snapshot(root, output_files)
    record = {key: assignment[key] for key in
              ('task', 'project', 'task_hash', 'attempt', 'role', 'actor', 'provider', 'model', 'effort', 'input_subject')}
    record.update(state=report['state'], output_snapshot=output, output_subject=output['subject'],
                  assignment=assignment_ref, report=report, native_reference=native_reference,
                  observer=observer, provenance='declared',
                  provenance_note='Native result must be independently checked by coordinator; this file is not host authentication',
                  finished_at=datetime.now(timezone.utc).isoformat())
    return append_record(root, 'outcome', record)


def handoff(root, *, task_ref, assignments, next_action, ownership, pending_external,
            public_files, notes):
    """Preserve a bounded continuation; never terminate, replay or reset anything."""
    text(next_action, 'next safe action')
    text(notes, 'handoff notes')
    if not isinstance(ownership, list) or not isinstance(pending_external, list):
        raise ValueError('Ownership and pending external actions must be explicit lists')
    read_record(root, task_ref)
    for ref in assignments:
        read_record(root, ref)
    for item in ownership:
        if not isinstance(item, dict) or item.get('state') not in ('active', 'absent', 'unknown'):
            raise ValueError('Explicit owner state required')
        text(item.get('reference'), 'owner reference')
    for item in pending_external:
        if not isinstance(item, dict) or item.get('state') not in ('not_started', 'confirmed', 'response_unknown'):
            raise ValueError('Explicit external effect state required')
        text(item.get('readback'), 'external readback next action')
    blocked = any(item['state'] != 'absent' for item in ownership)
    uncertain = any(item['state'] == 'response_unknown' for item in pending_external)
    return append_record(root, 'handoff', dict(
        task_ref=task_ref, assignments=assignments, next_action=next_action,
        ownership=ownership, pending_external=pending_external, notes=notes,
        source=snapshot(root, public_files),
        resume='RECONCILE_OWNER' if blocked else 'READBACK_FIRST' if uncertain else 'INSPECT_DIFF',
        created_at=datetime.now(timezone.utc).isoformat()))
