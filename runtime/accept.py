"""Evidence and acceptance written into the task file, bound to current source.

The tool, not the model, writes Evidence and Review lines. Every line carries
the digest of the task's Areas; acceptance recomputes it, so evidence taken on
other bytes is stale. Identities (Owner, reviewer) are declared, not
authenticated: the rule stops honest mistakes and casual self-review, not a
determined forger running as the same OS user.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex

from . import plan
from .paths import PRIVATE, public_path
from .verification import run_command

CHECK_RE = re.compile(r'^- \[machine\] check `([^`]+)` \| (PASS|FAIL) \|.*\| digest=([0-9a-f]+)')
EVIDENCE_RE = re.compile(r'^- \[([a-z_]+)\] (?!check `)(.*?)(?: \| files=([^|]+))? \| digest=([0-9a-f]+)')
REVIEW_RE = re.compile(r'^- review by (.+?) \| (PASS|BLOCKED) \| digest=([0-9a-f]+)')
FINDING_RE = re.compile(r'^- finding (BLOCKER|MAJOR|MINOR): (.+?)(?: \| accepted: (.+?) \| owner: (.+))?$')


def digest(root, areas):
    """Content digest of every tracked/untracked public file matched by Areas."""
    if not areas:
        raise ValueError('Task has no Areas; evidence cannot be bound to source')
    root = Path(root)
    files = sorted(f for f in plan.repo_files(root) if any(plan.matches(f, a) for a in areas)
                   and not PRIVATE.search(f))
    if not files:
        raise ValueError('Areas match no files: ' + ', '.join(areas))
    entries = [(f, hashlib.sha256((root / f).read_bytes()).hexdigest()) for f in files]
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()[:16], len(files)


def _stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _actor(task, actor, reviewer_may_check=False):
    """Only the Owner works an IN_PROGRESS task; on REVIEW the Owner or the latest reviewer may act."""
    actor = (actor or '').strip()
    if not actor:
        raise ValueError('--as <your model id> is required')
    allowed = {task['owner']}
    if task['status'] == 'REVIEW' and (rev := _latest_review(task['review'])):
        allowed.add(rev['reviewer'])
    if task['status'] == 'REVIEW' and reviewer_may_check:
        return  # a reviewer reruns Verify itself; acceptance still needs its review
    if actor not in allowed:
        raise ValueError(f"{task['id']} is owned by {task['owner'] or 'nobody'}: `start` it (with --takeover "
                         '"<reason>" if that owner stopped) before acting on it')


def check(root, task_id, timeout=None, actor=''):
    task = plan.find_task(root, task_id)
    if task['status'] in ('IN_PROGRESS', 'REVIEW'):
        _actor(task, actor, reviewer_may_check=True)
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}: `start` it first"]
    if not task['verify']:
        return 2, [f"FAIL {task['id']} has no backticked Verify command"]
    timeout = timeout or plan.load_config(root).get('check_timeout', 900)
    before, count = digest(root, task['areas'])
    results = []
    for n, cmd in enumerate(task['verify'], 1):
        log = f"runs/{task['id']}-{_stamp()}-{n}.log"
        r = run_command(root, shlex.split(cmd), plan.pdir(root) / log, timeout)
        results.append((cmd, r, log))
    after, _ = digest(root, task['areas'])
    out = []
    for cmd, r, log in results:
        ok = r['exit_code'] == 0 and before == after
        line = (f"- [machine] check `{cmd}` | {'PASS' if ok else 'FAIL'} | exit={r['exit_code']} | "
                f"{r['duration_seconds']}s | digest={after} | log={log}")
        plan.append_section(task['file'], 'Evidence', line)
        out.append(line[2:])
    if before != after:
        out.append('! Areas changed while checks ran; results are FAIL. Rerun on stable source.')
    passed = all(r['exit_code'] == 0 for _, r, _ in results) and before == after
    out.append(f"{'PASS' if passed else 'FAIL'}: {len(results)} command(s) on {count} file(s) in Areas")
    return (0 if passed else 1), out


def evidence(root, task_id, kind, note, files=(), actor=''):
    task = plan.find_task(root, task_id)
    _actor(task, actor)
    if kind not in plan.KINDS or kind == 'machine':
        raise ValueError('Kind must be one of ' + ', '.join(k for k in plan.KINDS if k != 'machine') +
                         '; machine evidence comes only from `check`')
    if not note.strip() or '|' in note or '\n' in note:
        raise ValueError('Note must be one nonempty line without "|"')
    hashed = []
    for name in files:
        path = public_path(root, name)
        if not path.is_file():
            raise ValueError('Evidence file missing: ' + name)
        hashed.append(f'{name}@{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}')
    value, _ = digest(root, task['areas'])
    line = f'- [{kind}] {note.strip()}' + (f" | files={','.join(hashed)}" if hashed else '') + f' | digest={value}'
    plan.append_section(task['file'], 'Evidence', line)
    return 0, [line[2:]]


def review(root, task_id, reviewer, verdict, findings=()):
    task = plan.find_task(root, task_id)
    reviewer = (reviewer or '').strip()
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}; nothing to review"]
    if not reviewer or not task['owner'] or reviewer == task['owner']:
        return 2, [f"FAIL reviewer must be named and differ from Owner ({task['owner'] or 'unset'}); "
                   'the implementing session cannot review itself under another name']
    if verdict not in ('PASS', 'BLOCKED'):
        raise ValueError('Verdict must be PASS or BLOCKED')
    for f in findings:
        m = FINDING_RE.match('- finding ' + f.strip())
        if not m:
            raise ValueError('Finding must be "BLOCKER|MAJOR|MINOR: text" with optional '
                             '" | accepted: reason | owner: user|SA-NNN" for MINOR')
        # A reviewer cannot approve its own exception: the user or a tracked follow-up task owns it.
        if m.group(4) and not (m.group(4).strip() == 'user' or (
                re.fullmatch(r'SA-\d{3,}', m.group(4).strip()) and
                (plan.pdir(root) / 'tasks' / (m.group(4).strip() + '.md')).is_file())):
            raise ValueError('Accepted MINOR owner must be "user" or an open follow-up task SA-NNN')
    value, _ = digest(root, task['areas'])
    lines = [f'- review by {reviewer} | {verdict} | digest={value}'] + [f'- finding {f.strip()}' for f in findings]
    for line in lines:
        plan.append_section(task['file'], 'Review', line)
    return 0, [line[2:] for line in lines]


def _latest_review(lines):
    block = None
    for line in lines:
        m = REVIEW_RE.match(line)
        if m:
            block = {'reviewer': m.group(1), 'verdict': m.group(2), 'digest': m.group(3), 'findings': []}
        elif block and (f := FINDING_RE.match(line)):
            block['findings'].append(f.groups())
    return block


def accept(root, task_id, actor=''):
    task = plan.find_task(root, task_id)
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}: only IN_PROGRESS or REVIEW tasks are accepted"]
    _actor(task, actor)
    if not task['owner']:
        return 2, [f"FAIL {task['id']} has no Owner; `start` records who implemented it"]
    current, _ = digest(root, task['areas'])
    problems, missing = [], []
    for item in task['open_items']:
        missing.append(f"open acceptance: [{item['kind']}] {item['text'][:70]}")
    latest = {}
    for line in task['evidence']:
        m = CHECK_RE.match(line)
        if m:
            latest[m.group(1)] = (m.group(2), m.group(3))
    kinds = {i['kind'] for i in task['items'] if i['done']}
    if 'machine' in kinds or task['verify']:
        for cmd in task['verify']:
            result, value = latest.get(cmd, (None, None))
            if result is None or value != current:
                missing.append(f'no check on current source for `{cmd}` (run `check`)')
            elif result == 'FAIL':
                problems.append(f'latest check failed: `{cmd}`')
    for kind in sorted(kinds - {'machine'}):
        found = [m for line in task['evidence'] if (m := EVIDENCE_RE.match(line))
                 and m.group(1) == kind and m.group(4) == current]
        if not found:
            missing.append(f'no {kind} evidence on current source (run `evidence`)')
        elif not any(all(_file_matches(root, ref) for ref in (m.group(3) or '').split(',') if ref.strip())
                     for m in found):
            problems.append(f'{kind} evidence file changed since it was observed')
    for e in task['external']:
        if e['state'] in ('sent', 'response_unknown', '?'):
            missing.append(f"external operation unresolved: {e['op'] or e['line']} -> readback first")
    rev = _latest_review(task['review'])
    if task['risk'] in ('MEDIUM', 'HIGH'):
        if rev is None or rev['digest'] != current:
            missing.append('independent review on current source required (MEDIUM/HIGH risk)')
        else:
            if rev['reviewer'] == task['owner']:
                problems.append('reviewer equals Owner')
            if rev['verdict'] != 'PASS':
                problems.append('review verdict BLOCKED')
            for severity, text_, reason, owner in rev['findings']:
                if severity != 'MINOR' or not reason or not owner:
                    problems.append(f'unresolved finding {severity}: {text_[:60]}')
    if task['risk'] not in plan.RISK_VALUES:
        problems.append('Risk must be LOW|MEDIUM|HIGH')
    if problems:
        return 2, [f'BLOCKED {task["id"]}'] + [f'  - {p}' for p in problems + missing]
    user_items = [i['text'] for i in task['open_items'] if i['kind'] == 'user_feedback']
    rest = [m for m in missing if not m.startswith(('open acceptance: [user_feedback]', 'independent review'))]
    if user_items and not rest:
        # Waiting for the user must not hold the single IN_PROGRESS slot.
        plan.set_header(task['file'], 'Status', 'BLOCKED')
        plan.set_header(task['file'], 'Blocked', 'user feedback: ' + user_items[0][:120])
        return 1, [f"WAITING_USER {task['id']}: everything else is current; set BLOCKED so other work can start. "
                   'When the user answers: `evidence --kind user_feedback`, tick the item, `start` and `accept`.']
    review_only = missing and all(m.startswith('independent review') for m in missing)
    if review_only:
        if task['status'] != 'REVIEW':
            plan.set_header(task['file'], 'Status', 'REVIEW')
        return 1, [f"REVIEW_PENDING {task['id']}: implementation evidence is current; a different, stronger agent "
                   f"runs `review {task['id']}` then `accept`. Commit now with SA-WIP: true if you stop here."]
    if missing:
        return 1, [f'UNVERIFIED {task["id"]}'] + [f'  - {m}' for m in missing]
    plan.set_header(task['file'], 'Status', 'DONE')
    plan.append_section(task['file'], 'Evidence', f'- accept: DONE | digest={current}')
    trailers = [f"SA-Task: {task['id']}", f"SA-Verification: {plan.VERIFICATION[task['risk']]}",
                f"SA-Agent: {task['owner']}"] + ([f"SA-Reviewer: {rev['reviewer']}"] if rev else [])
    return 0, [f"DONE {task['id']}", 'Commit code + this task file with these trailers (blank line before them):'] + \
        [f'  {t}' for t in trailers] + [
        'Add SA-Current-Checkpoint: <domains> if you reconciled current.md. After the commit succeeds, delete the '
        'task file in the next commit. Push per config git.push.']


def _file_matches(root, ref):
    name, _, short = ref.strip().rpartition('@')
    try:
        path = public_path(root, name)
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()[:16] == short
    except ValueError:
        return False
