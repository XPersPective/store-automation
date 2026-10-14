"""Run supervisor-written Verify commands and compare explicit release readback.

A Verify line is executable code: the strong model that writes the task selects
it after inspecting the project. Never execute commands taken from worker output.
"""
from datetime import datetime
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from .processes import ProcessTree

SECRET_ENV = re.compile(r'API_KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|_KEY$|^KEY$|_PAT$|DSN$|'
                        r'DATABASE_URL|_AUTH|AUTH_|COOKIE|OPENAI_BASE_URL|ANTHROPIC_BASE_URL', re.I)
# cmd.exe reads these in .cmd/.bat arguments as commands, quoting or expansions even without a shell.
BATCH_META = re.compile(r'[&|<>^%!"\r\n]')


def run_command(root, argv, log_path, timeout=900):
    """Run one argv in a kill-on-close process tree; full output goes to log_path."""
    if (not isinstance(argv, list) or not argv or
            any(not isinstance(s, str) or not s or '\x00' in s for s in argv)):
        raise ValueError('Explicit nonempty argv list required; no shell text')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 1800:
        raise ValueError('Timeout must be in (0, 1800] seconds')
    root = Path(root).resolve(strict=True)
    executable = argv[0]
    if os.path.dirname(executable):
        # Project scripts such as ./gradlew resolve in the project, not the caller's cwd.
        executable = str(root / executable)
    elif os.name == 'nt':
        # CreateProcess finds only .exe by bare name; npm, flutter and npx are .cmd/.bat.
        executable = shutil.which(executable) or executable
    if Path(executable).suffix.lower() in ('.cmd', '.bat'):
        # argv safety stops at the batch boundary: cmd.exe would read & and % as commands.
        injected = [s for s in argv[1:] if BATCH_META.search(s)]
        if injected:
            raise ValueError('Batch arguments must not contain & | < > ^ % ! " (cmd.exe injection): ' + injected[0])
    env = {k: v for k, v in os.environ.items() if not SECRET_ENV.search(k)}
    # A stale __pycache__ next to edited source can answer for code that no longer exists (equal size,
    # preserved mtime). Every run gets an empty bytecode cache, whichever tool (pytest, npm, make) starts Python.
    cache = tempfile.mkdtemp(prefix='sa-pycache-')
    env['PYTHONPYCACHEPREFIX'] = cache
    started = time.monotonic()
    tree = ProcessTree()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'wb') as log:
        proc, timed_out = None, False
        try:
            try:
                proc = tree.spawn([executable, *argv[1:]], cwd=root, env=env, stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT)
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
            finally:
                tree.close()
                if proc is not None:
                    proc.wait(timeout=10)
        finally:
            if cache:
                shutil.rmtree(cache, ignore_errors=True)
    return {'exit_code': 124 if timed_out else proc.returncode, 'timed_out': timed_out,
            'duration_seconds': round(time.monotonic() - started, 3),
            'containment': 'Windows JobObject' if os.name == 'nt' else 'POSIX process group'}


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be nonempty text')
    return value


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
