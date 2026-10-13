"""Run supervisor-selected local checks and compare explicit release readback.

An argv is executable code: only the coordinator selects it after inspecting
the project command. Never execute commands supplied by worker report text.
"""
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from .acceptance import text
from .processes import ProcessTree
from .receipts import append_record, snapshot, verify_snapshot


def run_check(root, argv, inputs, *, timeout=300):
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(s, str) or not s or '\x00' in s for s in argv)):
        raise ValueError('Explicit nonempty argv list required; no shell text')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 1800:
        raise ValueError('Timeout must be in (0, 1800] seconds')
    root = Path(root).resolve(strict=True)
    source = snapshot(root, inputs)
    env = {k: v for k, v in os.environ.items() if not re.search(
        r'API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|OPENAI_BASE_URL|ANTHROPIC_BASE_URL', k, re.I)}
    started = time.monotonic()
    wall = datetime.now(timezone.utc).isoformat()
    tree = ProcessTree()
    # ponytail: log bytes are kept in a temporary file; only the bounded tail is
    # retained. For untrusted noisy checks use an OS disk quota/sandbox.
    with tempfile.TemporaryFile() as log:
        proc = None
        timed_out = False
        try:
            proc = tree.spawn(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                              stdout=log, stderr=subprocess.STDOUT)
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            tree.close()
            if proc is not None:
                proc.wait(timeout=10)
        log.seek(0, 2)
        size = log.tell()
        log.seek(max(0, size - 16000))
        tail = log.read().decode('utf-8', errors='replace')
    stable = True
    try:
        verify_snapshot(root, source)
    except (ValueError, OSError):
        stable = False
    record = dict(command=argv, cwd=str(root), input_snapshot=source,
                  source_stable=stable, exit_code=124 if timed_out else proc.returncode,
                  state='FAIL' if timed_out or proc.returncode or not stable else 'PASS',
                  started_at=wall, duration_seconds=round(time.monotonic()-started, 6),
                  output_tail=tail, output_truncated=size > 16000,
                  claim='Only this local command and unchanged declared inputs',
                  containment='Windows JobObject' if os.name == 'nt' else 'POSIX process group; parent-death unverified')
    ref = append_record(root, 'check', record)
    return {'reference': ref, 'state': record['state'], 'exit_code': record['exit_code'],
            'source_stable': stable, 'duration_seconds': record['duration_seconds']}


def release_readback(expected, observed):
    """Compare an already-observed remote result; never upload or read secrets."""
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise ValueError('Explicit expected and observed release objects required')
    for key in ('platform', 'account', 'app', 'channel', 'version', 'artifact_sha256'):
        text(expected.get(key), 'expected ' + key)
    states = {'LOCAL_PREPARED', 'UPLOADED', 'SUBMITTED', 'APPROVED', 'AVAILABLE'}
    requested = text(expected.get('state'), 'expected release state')
    if requested not in states:
        raise ValueError('Unknown expected release state')
    actual = text(observed.get('state'), 'observed release state')
    if actual not in states:
        raise ValueError('Unknown observed release state')
    mismatch = [key for key in ('platform', 'account', 'app', 'channel', 'version', 'artifact_sha256')
                if observed.get(key) != expected[key]]
    missing = []
    if actual != requested:
        missing.append('Requested state not observed: ' + requested)
    text(observed.get('readback_reference'), 'readback reference')
    stamp = datetime.fromisoformat(text(observed.get('observed_at'), 'readback time'))
    if stamp.tzinfo is None:
        raise ValueError('Readback time must include timezone')
    if actual == 'AVAILABLE':
        text(observed.get('availability_reference'), 'availability reference')
    if observed.get('provenance') != 'verified':
        missing.append('Remote observation provenance unverified')
    return {'status': 'BLOCKED' if mismatch else 'UNVERIFIED' if missing else 'MATCHED',
            'state': actual, 'mismatch': mismatch, 'missing': missing,
            'claim': 'Recorded remote observation matches; supervisor must check freshness, this function did not contact a store'}


def measured_usage(attempts, expected_ids):
    """Only explicit disjoint native last-turn counters are added."""
    if not isinstance(attempts, list) or not isinstance(expected_ids, list):
        raise ValueError('Attempt and expected ID lists required')
    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError('Expected attempts contain duplicates')
    seen, fields = set(), ('input_tokens', 'output_tokens')
    totals = dict.fromkeys(fields, 0)
    complete = True
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ValueError('Attempt object required')
        identity = text(attempt.get('id'), 'attempt id')
        if identity in seen or identity not in expected_ids:
            raise ValueError('Duplicate or unexpected attempt')
        seen.add(identity)
        usage = attempt.get('usage')
        if attempt.get('usage_scope') != 'disjoint_last_turn' or not isinstance(usage, dict):
            complete = False
            continue
        for field in fields:
            value = usage.get(field)
            if value is None:
                complete = False
            elif type(value) is not int or value < 0:
                raise ValueError('Invalid usage counter')
            else:
                totals[field] += value
    complete = complete and seen == set(expected_ids)
    return {'complete': complete, 'totals': totals if complete else None,
            'observed_partial': totals, 'missing_attempts': sorted(set(expected_ids)-seen),
            'note': 'Account quota deltas and inclusive parent totals are not task usage'}
