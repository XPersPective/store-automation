"""Evidence and acceptance written into the task file, bound to current source and spec.

The tool, not the model, writes Evidence and Review lines. Every line carries
the digest of the task's Areas and of its contract (what it promises, without
progress): acceptance recomputes both, so evidence taken on other bytes or for
another spec is stale. A check line also names its log file and that log's hash,
so a hand-written PASS without the real run is refused. Identities (Owner,
reviewer, by=) are declared, not authenticated: the rules stop honest mistakes
and casual self-review, not a determined forger running as the same OS user.
"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shlex

from . import plan
from .paths import PRIVATE, public_path
from .verification import run_command

CHECK_RE = re.compile(r'^- \[machine\] check `(?P<cmd>[^`]+)` \| (?P<result>PASS|FAIL) \| exit=(?P<exit>-?\d+) \| '
                      r'[0-9.]+s \| by=(?P<by>[^|]*?) '
                      r'\| digest=(?P<digest>[0-9a-f]+) \| contract=(?P<contract>[0-9a-f]+) '
                      r'\| log=(?P<log>\S+)@(?P<hash>[0-9a-f]+)$')
EVIDENCE_RE = re.compile(r'^- \[(?P<kind>[a-z_]+)\] (?!check `)(?P<note>[^|]*?) \| criterion=(?P<criteria>[0-9a-f,]+)'
                         r'(?: \| files=(?P<files>[^|]+))? \| by=(?P<by>[^|]*?) \| digest=(?P<digest>[0-9a-f]+) '
                         r'\| contract=(?P<contract>[0-9a-f]+)$')
REVIEW_RE = re.compile(r'^- review by (.+?) \| (PASS|BLOCKED) \| digest=([0-9a-f]+) \| contract=([0-9a-f]+)$')
FINDING_RE = re.compile(r'^- finding (BLOCKER|MAJOR|QUALITY|MINOR): (.+?)(?: \| accepted: (.+?) \| owner: (.+))?$')
RISK_ORDER = {r: n for n, r in enumerate(plan.RISK_VALUES)}
LOG_FOOTER = '[store-automation check]'
SHOT_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.webm', '.mp4', '.mov')
RUNS_KEEP_DAYS, RUNS_KEEP_FILES = 14, 200


def digest(root, areas):
    """Content digest of every tracked/untracked public file matched by Areas.

    CRLF is hashed as LF (plan.areas_digest), so another core.autocrlf keeps the evidence.
    """
    if not areas:
        raise ValueError('Task has no Areas; evidence cannot be bound to source')
    root = Path(root)
    files = sorted(f for f in plan.repo_files(root) if any(plan.matches(f, a) for a in areas)
                   and not PRIVATE.search(f))
    if not files:
        raise ValueError('Areas match no files: ' + ', '.join(areas))
    # Linked or escaping paths inside Areas are refused before reading.
    return plan.areas_digest([(f, public_path(root, f).read_bytes()) for f in files]), len(files)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _log_path(root, task_id, n):
    """Exclusive log name: two checks in the same second never overwrite each other's raw output."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    runs = plan.pdir(root) / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    prune_runs(root)
    suffix = 1
    while True:
        path = runs / f"{task_id}-{stamp}-{n}{'' if suffix == 1 else f'-{suffix}'}.log"
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return path, f'runs/{path.name}'
        except FileExistsError:
            suffix += 1


def prune_runs(root):
    """Keep runs/ bounded: a log an open task still cites stays; the rest goes after RUNS_KEEP_DAYS, and the
    oldest beyond RUNS_KEEP_FILES go at once.

    ponytail: count/age caps, not a byte budget; a byte cap if single logs grow huge.
    """
    runs = plan.pdir(root) / 'runs'
    cited = {m['log'].split('/')[-1] for t in plan.list_tasks(root) if t['status'] != 'DONE'
             for line in t['evidence'] if (m := CHECK_RE.match(line))}
    logs = sorted((p for p in runs.glob('*.log') if p.name not in cited), key=lambda p: p.stat().st_mtime)
    cutoff = datetime.now(timezone.utc).timestamp() - RUNS_KEEP_DAYS * 86400
    for n, path in enumerate(logs):
        if path.stat().st_mtime < cutoff or len(logs) - n > RUNS_KEEP_FILES:
            path.unlink(missing_ok=True)


def _actor(task, actor, anyone_on_review=False):
    """Only the Owner works an IN_PROGRESS task; on REVIEW the Owner or the latest reviewer may act.

    `check` on REVIEW is open to any named agent: a reviewer reruns Verify before it reviews; the line
    records who ran it and acceptance still needs that review.
    """
    actor = plan.agent_id(actor, '--as')
    if task['status'] == 'REVIEW' and anyone_on_review:
        return actor
    allowed = {task['owner']}
    if task['status'] == 'REVIEW' and (rev := _latest_review(task['review'])):
        allowed.add(rev['reviewer'])
    if actor not in allowed:
        raise ValueError(f"{task['id']} is owned by {task['owner'] or 'nobody'}: `start` it (with --takeover "
                         '"<reason>" if that owner stopped) before acting on it')
    return actor


def check(root, task_id, timeout=None, actor=''):
    task = plan.find_task(root, task_id)
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}: `start` it first"]
    actor = _actor(task, actor, anyone_on_review=True)
    if not task['verify']:
        return 2, [f"FAIL {task['id']} has no backticked Verify command"]
    timeout = timeout or plan.load_config(root).get('check_timeout', 900)
    before, count = digest(root, task['areas'])
    contract = plan.contract(task)
    results = []
    for n, cmd in enumerate(task['verify'], 1):
        path, log = _log_path(root, task['id'], n)
        results.append((cmd, run_command(root, shlex.split(cmd), path, timeout), path, log))
    after, _ = digest(root, task['areas'])
    out = []
    for cmd, r, path, log in results:
        ok = r['exit_code'] == 0 and before == after
        with open(path, 'a', encoding='utf-8', newline='\n') as stream:  # the log states its own verdict
            stream.write(f"\n{LOG_FOOTER} {'PASS' if ok else 'FAIL'} exit={r['exit_code']} digest={after} "
                         f"contract={contract}\n")
        line = (f"- [machine] check `{cmd}` | {'PASS' if ok else 'FAIL'} | exit={r['exit_code']} | "
                f"{r['duration_seconds']}s | by={actor} | digest={after} | contract={contract} | "
                f"log={log}@{_hash(path)}")
        plan.append_section(task['file'], 'Evidence', line)
        out.append(line[2:])
    if before != after:
        out.append('! Areas changed while checks ran; results are FAIL. Rerun on stable source.')
    passed = all(r['exit_code'] == 0 for _, r, _, _ in results) and before == after
    out.append(f"{'PASS' if passed else 'FAIL'}: {len(results)} command(s) on {count} file(s) in Areas")
    return (0 if passed else 1), out


def evidence(root, task_id, kind, note, files=(), actor='', criteria=()):
    task = plan.find_task(root, task_id)
    actor = _actor(task, actor)
    if kind not in plan.KINDS or kind == 'machine':
        raise ValueError('Kind must be one of ' + ', '.join(k for k in plan.KINDS if k != 'machine') +
                         '; machine evidence comes only from `check`')
    if not note.strip() or '|' in note or '\n' in note:
        raise ValueError('Note must be one nonempty line without "|"')
    same_kind = [i['id'] for i in task['items'] if i['kind'] == kind]
    criteria = [c.strip().lower() for c in criteria if c.strip()] or (same_kind if len(same_kind) == 1 else [])
    if not criteria:
        known = ', '.join(same_kind) or f"no [{kind}] item in {task['id']}"
        raise ValueError(f'Name the Acceptance item(s) this observation proves: --criterion <id> '
                         f'({known}; ids are shown by `boot`)')
    wrong = [c for c in criteria if c not in same_kind]
    if wrong:
        raise ValueError(f"criterion {', '.join(wrong)} is no [{kind}] Acceptance item of {task['id']} "
                         f"(its [{kind}] items: {', '.join(same_kind) or 'none'})")
    if kind == 'visual' and not any(name.lower().endswith(SHOT_SUFFIXES) for name in files):
        raise ValueError('Visual evidence needs the rendered result: --file <screenshot or recording>; '
                         'reading source is not visual acceptance')
    if kind == 'interaction' and not files and note.count('->') < 2:
        raise ValueError('Interaction evidence needs what was really done: --file <recording or trace>, or a '
                         'note listing the steps and the result as "step -> step -> result"')
    hashed = []
    for name in files:
        path = public_path(root, name)
        if not path.is_file():
            raise ValueError('Evidence file missing: ' + name)
        hashed.append(f'{name}@{_hash(path)}')
    value, _ = digest(root, task['areas'])
    line = (f"- [{kind}] {note.strip()} | criterion={','.join(criteria)}" +
            (f" | files={','.join(hashed)}" if hashed else '') +
            f' | by={actor} | digest={value} | contract={plan.contract(task)}')
    plan.append_section(task['file'], 'Evidence', line)
    return 0, [line[2:]]


def implementers(task):
    """Everyone who started (owned) the task; none of them may review it."""
    return {r['owner'] for r in plan.start_records(task)} | ({task['owner']} if task['owner'] else set())


def review(root, task_id, reviewer, verdict, findings=(), models_path=None):
    task = plan.find_task(root, task_id)
    reviewer = plan.agent_id(reviewer, '--reviewer')
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}; nothing to review"]
    if not task['owner'] or reviewer in implementers(task):
        return 2, [f"FAIL reviewer must be named and must not have implemented {task['id']} "
                   f"({', '.join(sorted(implementers(task))) or 'no Owner'}); a session never reviews its own work"]
    if verdict not in ('PASS', 'BLOCKED'):
        raise ValueError('Verdict must be PASS or BLOCKED')
    from . import models
    models.gate(task, reviewer, 'review', models_path)
    for f in findings:
        m = FINDING_RE.match('- finding ' + f.strip())
        if not m:
            raise ValueError('Finding must be "BLOCKER|MAJOR|QUALITY|MINOR: text" with optional '
                             '" | accepted: reason | owner: user|SA-NNN" (QUALITY: owner user only)')
        # A reviewer cannot approve its own exception: the user or a tracked follow-up task owns it.
        owner = (m.group(4) or '').strip()
        if owner and not (owner == 'user' or (
                m.group(1) == 'MINOR' and re.fullmatch(r'SA-\d{3,}', owner) and
                (plan.pdir(root) / 'tasks' / (owner + '.md')).is_file())):
            raise ValueError('Accepted MINOR owner must be "user" or an open follow-up task SA-NNN; '
                             'an accepted QUALITY gap is owned by the user only')
    value, _ = digest(root, task['areas'])
    lines = [f'- review by {reviewer} | {verdict} | digest={value} | contract={plan.contract(task)}'] + \
            [f'- finding {f.strip()}' for f in findings]
    for line in lines:
        plan.append_section(task['file'], 'Review', line)
    return 0, [line[2:] for line in lines]


def _latest_review(lines):
    block = None
    for line in lines:
        m = REVIEW_RE.match(line)
        if m:
            block = {'reviewer': m.group(1), 'verdict': m.group(2), 'digest': m.group(3),
                     'contract': m.group(4), 'findings': []}
        elif block and (f := FINDING_RE.match(line)):
            block['findings'].append(f.groups())
    return block


def effective_risk(task):
    """Risk never drops below what any `start` recorded: lowering it after work began skips no review."""
    risks = [task['risk']] + [r['risk'] for r in plan.start_records(task)]
    return max((r for r in risks if r in RISK_ORDER), key=RISK_ORDER.get, default=task['risk'])


def accept(root, task_id, actor='', models_path=None):
    task = plan.find_task(root, task_id)
    if task['status'] not in ('IN_PROGRESS', 'REVIEW'):
        return 2, [f"FAIL {task['id']} is {task['status']}: only IN_PROGRESS or REVIEW tasks are accepted"]
    _actor(task, actor)
    from . import models
    models.gate(task, actor, 'accept', models_path)
    if not task['owner']:
        return 2, [f"FAIL {task['id']} has no Owner; `start` records who implemented it"]
    errors = plan.task_errors(task)  # the grammar validate enforces: no empty Verify, unknown kind/state
    if errors:
        return 2, [f'BLOCKED {task["id"]}'] + [f'  - {e}' for e in errors]
    current, _ = digest(root, task['areas'])
    contract = plan.contract(task)
    risk = effective_risk(task)
    problems, missing = [], []
    for item in task['open_items']:
        missing.append(f"open acceptance: [{item['kind']}] {item['text'][:70]} (criterion {item['id']})")
    latest = {}
    for line in task['evidence']:
        if m := CHECK_RE.match(line):
            latest[m['cmd']] = m
    for cmd in task['verify']:
        m = latest.get(cmd)
        if m is None or m['digest'] != current or m['contract'] != contract:
            missing.append(f'no check on current source and spec for `{cmd}` (run `check`)')
        elif not (log := plan.pdir(root) / m['log']).is_file():
            missing.append(f'log of the latest `{cmd}` check is not in this checkout (other machine?): run `check`')
        elif _hash(log) != m['hash'] or not log.read_text(encoding='utf-8', errors='replace').rstrip().endswith(
                f"{LOG_FOOTER} {m['result']} exit={m['exit']} digest={m['digest']} contract={m['contract']}"):
            problems.append(f'`{cmd}` check line does not match its log: evidence is written only by `check`')
        elif m['result'] == 'FAIL':
            problems.append(f'latest check failed: `{cmd}`')
    for item in task['items']:  # one observation never closes a criterion it does not name
        if not item['done'] or item['kind'] == 'machine':
            continue
        found = [m for line in task['evidence'] if (m := EVIDENCE_RE.match(line)) and m['kind'] == item['kind']
                 and m['digest'] == current and m['contract'] == contract and item['id'] in m['criteria'].split(',')]
        if not found:
            missing.append(f"no evidence for criterion {item['id']} ([{item['kind']}] {item['text'][:60]}) on "
                           f"current source and spec: `evidence --kind {item['kind']} --criterion {item['id']}`")
        elif not any(all(_file_matches(root, ref) for ref in (m['files'] or '').split(',') if ref.strip())
                     for m in found):
            problems.append(f"criterion {item['id']} evidence file changed since it was observed")
    for e in task['external']:
        if e['state'] in ('sent', 'response_unknown'):
            missing.append(f"external operation unresolved: {e['op'] or e['line']} -> readback first")
    rev = _latest_review(task['review'])
    if risk in ('MEDIUM', 'HIGH'):
        if rev is None or rev['digest'] != current or rev['contract'] != contract:
            missing.append(f'independent review on current source and spec required ({risk} risk'
                           f"{', recorded at start' if risk != task['risk'] else ''})")
        else:
            if rev['reviewer'] in implementers(task):
                problems.append(f"reviewer {rev['reviewer']} implemented this task")
            if rev['verdict'] != 'PASS':
                problems.append('review verdict BLOCKED')
            for severity, text_, reason, owner in rev['findings']:
                accepted = severity == 'MINOR' and reason and owner or \
                    severity == 'QUALITY' and reason and (owner or '').strip() == 'user'
                if not accepted:
                    problems.append(f'unresolved finding {severity}: {text_[:60]}')
    if problems:
        return 2, [f'BLOCKED {task["id"]}'] + [f'  - {p}' for p in problems + missing]
    user_items = [i['text'] for i in task['open_items'] if i['kind'] == 'user_feedback']
    rest = [m for m in missing if not m.startswith(('open acceptance: [user_feedback]', 'independent review'))]
    if user_items and not rest:
        # Waiting for the user must not hold the single IN_PROGRESS slot; whoever resumes starts it anew.
        plan.set_headers(task['file'], {'Status': 'BLOCKED', 'Blocked': 'user feedback: ' + user_items[0][:120],
                                        'Owner': ''})
        return 1, [f"WAITING_USER {task['id']}: everything else is current; BLOCKED with an empty Owner so other "
                   'work can start. When the user answers: `start`, `evidence --kind user_feedback`, tick the '
                   'item, `accept`. Whoever started it may not review it.']
    review_only = missing and all(m.startswith('independent review') for m in missing)
    if review_only:
        if task['status'] != 'REVIEW':
            plan.set_header(task['file'], 'Status', 'REVIEW')
        return 1, [f"REVIEW_PENDING {task['id']}: implementation evidence is current; a different, stronger agent "
                   f"that did not implement it runs `review {task['id']}` then `accept`. Commit now with "
                   'SA-WIP: true if you stop here; on a single-agent host tell the user a second session must review.']
    if missing:
        return 1, [f'UNVERIFIED {task["id"]}'] + [f'  - {m}' for m in missing]
    plan.set_header(task['file'], 'Status', 'DONE')
    plan.append_section(task['file'], 'Evidence', f'- accept: DONE | digest={current} | contract={contract}')
    trailers = [f"SA-Task: {task['id']}", f"SA-Verification: {plan.VERIFICATION[risk]}",
                f"SA-Agent: {task['owner']}"] + ([f"SA-Reviewer: {rev['reviewer']}"] if rev else [])
    return 0, [f"DONE {task['id']}", 'Commit code + this task file with these trailers (blank line before them):'] + \
        [f'  {t}' for t in trailers] + [
        'Add SA-Current-Checkpoint: <domains> if you reconciled current.md. If a pre-commit hook rewrote staged '
        'files, the evidence no longer matches the commit: `check` and `accept` again before pushing. After '
        'the commit succeeds, delete the task file in the next commit. Push per config git.push.']


def _file_matches(root, ref):
    name, _, short = ref.strip().rpartition('@')
    try:
        path = public_path(root, name)
        return path.is_file() and _hash(path) == short
    except ValueError:
        return False
