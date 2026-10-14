"""Git-native plan memory: product, current architecture, tasks and checkpoints.

Adapted from Project Brain 2.1 (same author, MIT) and owned here. State lives in
.store-automation/ files and commit trailers; runs/ is the only untracked part.
Every command returns (exit_code, lines): 0 ok, 1 warnings, 2 errors, 3 no plan.
"""
import fnmatch
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .paths import PRIVATE

DIR = '.store-automation'
STATUS_VALUES = ('PLANNED', 'READY', 'IN_PROGRESS', 'REVIEW', 'BLOCKED', 'DONE')
RISK_VALUES = ('LOW', 'MEDIUM', 'HIGH')
PRIORITY_VALUES = ('P1', 'P2', 'P3')
TIER_VALUES = ('L', 'M', 'H')
KINDS = ('machine', 'interaction', 'visual', 'accessibility', 'security', 'integration',
         'artifact', 'remote', 'user_feedback')
EXTERNAL_STATES = ('not_started', 'sent', 'confirmed', 'response_unknown')
VERIFICATION = {'LOW': 'local', 'MEDIUM': 'domain', 'HIGH': 'global'}
VAGUE_RE = re.compile(r'\b(etc\.|improve|clean ?up|refactor as needed|handle properly|as discussed|'
                      r'vb\.|iyileştir\w*|düzenle\w*)', re.I)
TASK_FILE_RE = re.compile(r'^SA-(\d+)\.md$')
ADR_FILE_RE = re.compile(r'^ADR-(\d+)\.md$')
HEADER_RE = re.compile(r'^(status|priority|tier|risk|milestone|depends|owner|areas|domains|blocked):\s*(.*)$', re.I)
ACCEPT_RE = re.compile(r'^\s*- \[([ xX])\]\s*(?:\[([a-z_]+)\])?\s*(.*)$')
EXTERNAL_RE = re.compile(r'^\s*- (.+?)\s*\|\s*([a-z_]+)\s*\|\s*readback:\s*(.+)$')
READY_BY_RE = re.compile(r'^\s*- ready by (.+?):', re.I)
START_RE = re.compile(r'^- start by (?P<owner>.+?) \| risk=(?P<risk>[A-Z]*) \| contract=(?P<contract>[0-9a-f]+)$')
# Words that make a task HIGH risk (§2 of plan.md); small models tend to rate them lower.
HIGH_RISK_RE = re.compile(r'\b(auth\w*|login|password|token|session|crypto\w*|encrypt\w*|migration\w*|'
                          r'persist\w*|sqlite|database|payment\w*|billing|permission\w*|'
                          r'kimlik|şifre\w*|oturum|ödeme\w*|veritaban\w*|yetki\w*)\b', re.I)
# Acceptance that a weak implementer must not judge alone: risk or an outside contract.
SECURE_KINDS = ('security', 'integration', 'remote')
BUDGETS = {'current': 200, 'product': 150, 'constraints': 100, 'task': 120, 'open_tasks': 25}
SKIP_DIRS = {'.git', '.hg', '.svn', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build',
             '.next', '.nuxt', 'target', 'coverage', '.pytest_cache', '.mypy_cache', '.ruff_cache',
             '.turbo', '.cache', '.idea', '.gradle', 'bin', 'obj', '.dart_tool', '.pub-cache', DIR}

CURRENT_TMPL = """# Current Architecture

Verified present reality only. Markers: VERIFIED | OBSERVED | INFERRED | STALE | UNKNOWN.

## Runtime
- <language, framework, entry points>

## Map
<!-- path — role. Orientation index: read this instead of exploring. <=40 lines. -->
- `<path>` — <role>

## Domains

### <domain>
Status: UNKNOWN
Sources: `<src/domain/**>`, `<tests/domain/**>`
- <components, data flow, boundaries; terse, path:symbol refs>

## Known Unknowns
- <only unknowns that can change future work>
"""

PRODUCT_TMPL = """# Product
Status: DRAFT

Confirmed intent only. DRAFT until the user confirms the Goal. Unknown -> Open Decisions.

## Goal
<the user's goal, in their words; only the user changes it>

## Users
- <who, in which situation>

## Core Journeys
- <journey: start -> steps -> observable result>

## Platforms
- <android | ios | windows | macos | linux | web | cli: channel (store, installer, package, internal, none)>

## Success Conditions
- [interaction] <observable condition>

## Riskiest Assumptions
- RA-1: <assumption that would be most expensive if wrong -> cheapest probe; an M1 task names RA-1>

## Target State
### <domain>
- <intended end state>

## Non-Goals
- <what will not be built>

## Open Decisions
- OD-001 OPEN: <question> -> blocks <task/area>
"""

CONSTRAINTS_TMPL = """# Constraints

Only rules that change decisions. One line each, with source.

- C-001: <rule> (source: user | config | convention)
"""

TASK_TMPL = """# {id} — {title}
Status: PLANNED
Priority: {priority}
Tier: {tier}
Risk: {risk}
Milestone: {milestone}
Depends: {deps}
Owner:
Areas: <`src/x/**`, `tests/x/**`>
Domains: <domain>

## Objective
<what and why, in the user's words>

## Steps
1. <exact path, symbol and change; one action per step>

## Acceptance
- [ ] [machine] <observable condition>

## Verify
- `<command>`

## Escalate if
- <change that needs a user decision>

## External

## Evidence

## Review

## Notes
"""

# Unfilled template text: exactly the <...> tokens our own templates contain, so command syntax such as
# `--owner <id>` written by an agent is never mistaken for a leftover.
TEMPLATE_TOKENS = {t for t in re.findall(r'<[^<>\n]+>', CURRENT_TMPL + PRODUCT_TMPL + CONSTRAINTS_TMPL + TASK_TMPL)
                   if not t.startswith('<!')}


def has_placeholder(text):
    return any(token in text for token in TEMPLATE_TOKENS)


# Foreign planning systems `boot` reports and `legacy` retires: path -> (system, carries plan content that
# must be extracted first). Kept here so plan never imports legacy.
LEGACY_MARKERS = {
    '.project-brain': ('Project Brain', True),
    'PROJECT_BRAIN.md': ('Project Brain (single file)', True),
    '.taskmaster': ('Task Master', True),
    'memory-bank': ('Cline memory bank', True),
    '.kiro/specs': ('Kiro specs', True),
    '.factory': ('Store Automation 2.x', False),
    '.factory-bootstrap.json': ('Store Automation 2.x', False),
}


def legacy_found(root):
    return [n for n in LEGACY_MARKERS if (Path(root) / n).exists() or (Path(root) / n).is_symlink()]


POINTER_MARK = '<!-- store-automation -->'
POINTER = POINTER_MARK + """
## Store Automation
This project keeps its plan and state in `.store-automation/` (product, current architecture, open tasks).
Before any work, load the `store-automation` skill and run `store.py boot`; follow it for all work here.
"""


# ── helpers ──────────────────────────────────────────────────────────────

def git(root, *args, timeout=60):
    """Run git; stdout (right-stripped) or None on failure."""
    try:
        r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.rstrip() if r.returncode == 0 else None


def git_paths(root, *args):
    out = git(root, args[0], '-z', *args[1:])
    return None if out is None else [p for p in out.split('\0') if p]


def has_git(root):
    return git(root, 'rev-parse', '--is-inside-work-tree') == 'true'


def read(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def read_raw(path):
    """Text with its line endings untouched, for rewriting a file in place."""
    with open(path, encoding='utf-8', errors='replace', newline='') as stream:
        return stream.read()


def agent_id(value, flag):
    """A declared model/agent id: one short printable token run, safe inside `|`-separated plan lines."""
    value = (value or '').strip()
    if not re.fullmatch(r'[\w.:@/+-][\w .:@/+-]{0,79}', value) or value.endswith(' '):
        raise ValueError(f'{flag} <your model/agent id> is required: letters, digits and . : @ / + - _ '
                         'or spaces, at most 80 characters (e.g. claude-opus-5-5)')
    return value


def areas_digest(contents):
    """Digest over (path, bytes) pairs; CRLF hashed as LF so another core.autocrlf keeps the evidence.

    ponytail: a binary differing only in CRLF/LF hashes equal; use git-normalized blob hashes if that matters.
    """
    entries = [(f, hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()) for f, data in sorted(contents)]
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()[:16]


def norm_id(n):
    return f'SA-{int(n):03d}'


def criterion_id(kind, text):
    """Stable id per Acceptance item: same kind+text -> same id, whatever else in the task changed."""
    return hashlib.sha256(f'{kind}|{text}'.encode()).hexdigest()[:6]


def norm_domain(s):
    return re.sub(r'[\s_]+', '-', s.strip().strip('`*#').strip().lower())


def matches(path, pat):
    """Glob (* crosses /) or path/directory prefix."""
    pat = pat.strip()
    pat = pat[2:] if pat.startswith('./') else pat
    if any(c in pat for c in '*?['):
        # `**/x` also matches x at the root, as git and shell globs do.
        return fnmatch.fnmatchcase(path, pat) or (pat.startswith('**/') and fnmatch.fnmatchcase(path, pat[3:]))
    return path == pat or path.startswith(pat.rstrip('/') + '/')


def sections(text):
    out, cur = {'': []}, ''
    for line in text.splitlines():
        if line.startswith('## '):
            cur = line[3:].strip().lower()
            out.setdefault(cur, [])
        else:
            out[cur].append(line)
    return out


def first_line(lines):
    return next((line.strip() for line in lines if line.strip()), '')


def split_list(s):
    ticks = re.findall(r'`([^`]+)`', s)
    if ticks:
        return ticks
    return [x.strip() for x in s.split(',') if x.strip() and x.strip() not in ('-', 'None', 'none')]


def pdir(root):
    return Path(root) / DIR


def plan_exists(root):
    return (pdir(root) / 'current.md').is_file()


def load_config(root):
    path = pdir(root) / 'config.json'
    if not path.is_file():
        return {'commands': {}, 'git': {'commit': 'auto', 'push': 'auto'}, 'check_timeout': 900}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or not isinstance(data.get('commands', {}), dict) or \
            not isinstance(data.get('git', {}), dict):
        raise ValueError('config.json: commands and git must be objects')
    return data


def repo_files(root, git_ok=None):
    if git_ok is None:
        git_ok = has_git(root)
    if git_ok:
        files = git_paths(root, 'ls-files', '--cached', '--others', '--exclude-standard')
        if files is not None:
            return [f for f in files if not f.startswith(DIR + '/') and (Path(root) / f).is_file()]
    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        rel = os.path.relpath(dp, root).replace(os.sep, '/')
        files += [fn if rel == '.' else f'{rel}/{fn}' for fn in fns]
    return files


# ── tasks ────────────────────────────────────────────────────────────────

def parse_task(path, text=None):
    text = read(path) if text is None else text
    if text is None:
        return None
    sec = sections(text)
    head = {}
    for line in sec['']:
        m = HEADER_RE.match(line.strip())
        if m:
            head.setdefault(m.group(1).lower(), m.group(2).strip())
    title = next((line[2:].strip() for line in sec[''] if line.startswith('# ')), Path(path).stem)
    title = re.sub(r'^SA-\d+\s*[—–-]\s*', '', title)
    raw = head.get('status', '')
    token = raw.split()[0].upper() if raw.split() else '?'
    status = token if token in STATUS_VALUES else '?'
    acc = sec.get('acceptance', [])
    items = []
    for line in acc:
        m = ACCEPT_RE.match(line)
        if m:
            items.append({'done': m.group(1) != ' ', 'kind': m.group(2) or '', 'text': m.group(3).strip(),
                          'id': criterion_id(m.group(2) or '', m.group(3).strip())})
    resume = sec.get('resume', [])
    nxt = next((m.group(1).strip() for line in resume
                if (m := re.match(r'^\s*next:\s*(.*)$', line, re.I))), '')
    external = []
    for line in sec.get('external', []):
        if line.strip():
            m = EXTERNAL_RE.match(line)
            external.append({'line': line.strip(), 'op': m.group(1) if m else '',
                             'state': m.group(2) if m else '?', 'readback': m.group(3) if m else ''})
    steps = [line for line in sec.get('steps', []) if line.strip()]
    verify = [m.group(1) for line in sec.get('verify', []) if (m := re.match(r'^\s*- `([^`]+)`', line))]
    m = TASK_FILE_RE.match(Path(path).name)
    return {
        'id': norm_id(m.group(1)) if m else Path(path).stem, 'file': Path(path), 'title': title,
        'status': status, 'status_note': raw[len(token):].strip() if status != '?' else raw,
        'priority': head.get('priority', '').upper()[:2] if head.get('priority', '').upper()[:2]
        in PRIORITY_VALUES else 'P2', 'priority_raw': head.get('priority', ''),
        'tier': head.get('tier', '').upper()[:1], 'risk': head.get('risk', '').upper(),
        'milestone': head.get('milestone', ''), 'owner': head.get('owner', ''),
        'deps': [norm_id(n) for n in re.findall(r'SA-(\d+)', head.get('depends', ''))],
        'areas': split_list(head.get('areas', '')),
        'domains': [norm_domain(d) for d in split_list(head.get('domains', '')) if d.strip()],
        'blocked': head.get('blocked', '').strip('- '), 'items': items,
        'open_items': [i for i in items if not i['done']], 'steps': steps, 'verify': verify,
        'external': external, 'evidence': [line.strip() for line in sec.get('evidence', []) if line.strip()],
        'review': [line.strip() for line in sec.get('review', []) if line.strip()],
        'next': nxt, 'lines': len(text.splitlines()), 'text': text,
        'ready_by': next((m.group(1).strip() for line in sec.get('notes', []) if (m := READY_BY_RE.match(line))), ''),
        'vague': sorted({m.group(1).lower() for m in VAGUE_RE.finditer('\n'.join(steps + acc))}),
        'header_id': re.findall(r'^# (SA-\d+)', text, re.M),
    }


def list_tasks(root):
    d = pdir(root) / 'tasks'
    if not d.is_dir():
        return []
    tasks = [parse_task(f) for f in d.iterdir() if TASK_FILE_RE.match(f.name)]
    return sorted((t for t in tasks if t), key=lambda t: int(t['id'][3:]))


def find_task(root, task_id):
    m = re.fullmatch(r'(?:SA-)?(\d+)', task_id.strip(), re.I)
    if not m:
        raise ValueError('Task id must look like SA-007')
    path = pdir(root) / 'tasks' / (norm_id(m.group(1)) + '.md')
    if not path.is_file():
        raise ValueError('No open task file: ' + path.name)
    return parse_task(path)


def contract(task):
    """Digest of what the task promises, without its progress: changing the spec invalidates evidence.

    Status, Owner, Priority, ticks, Evidence, Review, Notes, Resume and External are working state;
    Objective, Steps, typed Acceptance, Verify, Escalate, Areas, Risk and Tier are the contract, so a
    reworded Acceptance, a lowered Risk or narrowed Areas never ride on an old check or review.
    """
    parts = sections(task['text'])
    spec = [f'{key}\n' + '\n'.join(line.strip() for line in parts.get(key, []) if line.strip())
            for key in ('objective', 'steps', 'verify', 'escalate if')]
    spec.append('acceptance\n' + '\n'.join(f"- [{i['kind']}] {i['text']}" for i in task['items']))
    spec.append(f"areas={task['areas']}\nrisk={task['risk']}\ntier={task['tier']}")
    return hashlib.sha256('\n'.join(spec).encode()).hexdigest()[:16]


def start_records(task):
    """The `- start by <owner> | risk=<R> | contract=<hex>` Notes lines `start` wrote, oldest first."""
    return [m.groupdict() for line in sections(task['text']).get('notes', [])
            if (m := START_RE.match(line.strip()))]


def task_errors(task):
    """Hard grammar invariants, shared by validate and accept so neither can be softer than the other."""
    tid, errors = task['id'], []
    if task['status'] == '?':
        errors.append(f"{tid}: no valid Status (first word must be {'|'.join(STATUS_VALUES)})")
    if task['risk'] not in RISK_VALUES:
        errors.append(f'{tid}: Risk must be LOW|MEDIUM|HIGH')
    for item in task['items']:
        if item['kind'] not in KINDS:
            errors.append(f"{tid}: acceptance item needs a kind tag [{'|'.join(KINDS)}]: {item['text'][:50]}")
    for e in task['external']:
        if e['state'] not in EXTERNAL_STATES:
            errors.append(f"{tid}: External line must be `- <op> | <{'|'.join(EXTERNAL_STATES)}> | readback: <how>`")
    if task['status'] in ('READY', 'IN_PROGRESS', 'REVIEW'):
        missing = [n for n, ok in (('Steps', task['steps']), ('Acceptance', task['items']),
                                   ('a backticked Verify command', task['verify']), ('Areas', task['areas'])) if not ok]
        if missing:
            errors.append(f"{tid}: {task['status']} but not an executable spec: missing {', '.join(missing)}")
    if task['status'] in ('IN_PROGRESS', 'REVIEW') and not task['owner']:
        errors.append(f"{tid}: {task['status']} without Owner (use `start`)")
    return errors


def set_header(path, key, value):
    set_headers(path, {key: value})


def set_headers(path, values):
    """Replace several header lines in one atomic write: never a half-updated identity."""
    lines = read_raw(path).splitlines(keepends=True)
    eol = _eol(lines)
    end = next((i for i, line in enumerate(lines) if line.startswith('## ')), len(lines))
    rest = {k.lower(): (k, v) for k, v in values.items()}
    for i in range(end):
        m = re.match(r'^([A-Za-z]+):', lines[i])
        if m and m.group(1).lower() in rest:
            key, value = rest.pop(m.group(1).lower())
            lines[i] = f'{key}: {value}'.rstrip() + eol
    for key, value in reversed(list(rest.values())):  # keys that were absent go before the first section
        lines.insert(max(1, min(end, 2)), f'{key}: {value}'.rstrip() + eol)
    write_atomic(path, ''.join(lines))


def _eol(lines):
    """A CRLF task file stays CRLF: one header edit must not rewrite every line."""
    return '\r\n' if lines and lines[0].endswith('\r\n') else '\n'


@contextmanager
def checkout_lock(root):
    """One writer per checkout: an exclusive lock around read-check-write of task identity.

    ponytail: single whole-checkout lock with a 10s wait and 30s stale break; per-task locks or a
    lock service are not worth it because one IN_PROGRESS task is the protocol anyway.
    """
    runs = Path(root) / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    lock = runs / 'writer.lock'
    deadline = time.monotonic() + 10
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f'{os.getpid()} {time.time()}'.encode())
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 30:  # a crashed holder left it behind
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise ValueError('another writer is starting a task in this checkout; retry in a moment')
            time.sleep(.1)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def append_section(path, heading, entry):
    """Append one line at the end of a '## heading' section, creating it if absent."""
    lines = read_raw(path).splitlines(keepends=True)
    eol = _eol(lines)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += eol
    start = next((i for i, line in enumerate(lines) if line.strip().lower() == '## ' + heading.lower()), None)
    if start is None:
        lines += ([eol] if lines and lines[-1].strip() else []) + [f'## {heading}{eol}', entry + eol]
    else:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
        insert = end
        while insert > start + 1 and not lines[insert - 1].strip():
            insert -= 1
        lines.insert(insert, entry + eol)
    write_atomic(path, ''.join(lines))


def write_atomic(path, text):
    """A crash leaves either the old or the new file, never half of one."""
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    if os.name != 'nt':  # make the rename durable too; Windows has no directory handle for this
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


# ── git state ────────────────────────────────────────────────────────────

def git_records(root, grep, *rev):
    out = git(root, 'log', *rev, f'--grep={grep}', '--format=%H%x1f%B%x1e')
    recs = []
    for r in (out or '').split('\x1e'):
        if '\x1f' in r:
            sha, body = r.split('\x1f', 1)
            recs.append((sha.strip(), body))
    return recs


def trailer_values(body, key):
    return [m.group(1).strip() for m in re.finditer(rf'^{key}:\s*(.+)$', body, re.M)]


def is_wip(body):
    return 'true' in [v.lower() for v in trailer_values(body, 'SA-WIP')]


def task_ids_in(body):
    return [norm_id(n) for v in trailer_values(body, 'SA-Tasks?') for n in re.findall(r'SA-(\d+)', v)]


def cat_files(root, specs, raw=False):
    """`<rev>:<path>` -> text (bytes if raw), None when absent, for many objects in one git process; None if git failed."""
    if not specs:
        return {}
    try:
        r = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'], input=''.join(s + '\n' for s in specs)
                           .encode(), capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode:
        return None
    out, data, pos = {}, r.stdout, 0
    for spec in specs:
        end = data.index(b'\n', pos)
        head, pos = data[pos:end].split(), end + 1
        if len(head) != 3:  # `<spec> missing` / `ambiguous`
            out[spec] = None
            continue
        size = int(head[2])
        out[spec] = data[pos:pos + size] if raw else data[pos:pos + size].decode('utf-8', 'replace')
        pos += size + 1
    return out


_HISTORY = {}


def task_history(root):
    """[(sha, body, closed ids)] for SA-Task commits, newest first; one pass per HEAD, shared by every caller.

    Closed = the commit is verified (not WIP) and the task file is absent in that commit, or present
    there as DONE with Evidence; never mere absence in today's worktree.
    """
    key = (str(root), git(root, 'rev-parse', '-q', '--verify', 'HEAD'))
    if key in _HISTORY:
        return _HISTORY[key]
    recs = [(sha, body, set(task_ids_in(body))) for sha, body in git_records(root, 'SA-Task')]
    verified = {sha for sha, body, _ in recs
                if not is_wip(body) and set(trailer_values(body, 'SA-Verification')) & set(VERIFICATION.values())}
    blobs = cat_files(root, [f'{sha}:{DIR}/tasks/{tid}.md' for sha, _, ids in recs if sha in verified
                             for tid in sorted(ids)])
    out = []
    for sha, body, ids in recs:
        closed = set()
        if sha in verified and blobs is not None:
            for tid in ids:
                text = blobs[f'{sha}:{DIR}/tasks/{tid}.md']
                if text is None or ((t := parse_task(Path(f'{tid}.md'), text))['status'] == 'DONE' and t['evidence']):
                    closed.add(tid)
        out.append((sha, body, closed))
    _HISTORY[key] = out
    return out


def committed_drift(root):
    """The newest DONE commit whose committed Areas bytes differ from what `accept` verified, else None.

    A pre-commit hook that rewrites files, or Areas files left out of the commit, makes the commit
    differ from the evidence; boot says so instead of letting it pass as verified.
    """
    for sha, body, closed in task_history(root):
        for tid in sorted(closed):
            text = (cat_files(root, [f'{sha}:{DIR}/tasks/{tid}.md']) or {}).get(f'{sha}:{DIR}/tasks/{tid}.md')
            m = text and re.search(r'^- accept: DONE \| digest=([0-9a-f]+)', text, re.M)
            if not m:
                continue
            task = parse_task(Path(f'{tid}.md'), text)
            names = [f for f in git_paths(root, 'ls-tree', '-r', '--name-only', sha) or []
                     if not f.startswith(DIR + '/') and not PRIVATE.search(f)
                     and any(matches(f, a) for a in task['areas'])]
            blobs = cat_files(root, [f'{sha}:{f}' for f in names], raw=True) or {}
            got = areas_digest([(f, blobs.get(f'{sha}:{f}') or b'') for f in names])
            return None if got == m.group(1) else (tid, sha[:7])
        if closed:
            return None
    return None


def history_task_ids(root):
    every, done = set(), set()
    for _, body, closed in task_history(root):
        every |= set(task_ids_in(body))
        done |= closed
    names = git(root, 'log', '--format=', '--name-only', '--', f'{DIR}/tasks') or ''
    every.update(norm_id(m.group(1)) for p in names.splitlines() if (m := TASK_FILE_RE.match(Path(p).name)))
    return every, done


def recent_closed(root, open_ids, n=3):
    out, seen = [], set(open_ids)
    for sha, body, closed in task_history(root):
        ids = sorted(closed - seen)
        seen.update(ids)
        if ids:
            out.append((','.join(ids), (trailer_values(body, 'SA-Agent') or ['?'])[0], sha[:7]))
            if len(out) >= n:
                break
    return out


def closed_since_audit(root, open_ids):
    last = git(root, 'log', '-1', '--grep=SA-Plan-Audit:', '--format=%H')
    since = set((git(root, 'rev-list', f'{last}..HEAD') or '').split()) if last else None
    ids = set()
    for sha, _, closed in task_history(root):
        if since is None or sha in since:
            ids |= closed
    return len(ids - open_ids)


def checkpoint_base(root):
    for sha, body in git_records(root, 'SA-Current-Checkpoint:'):
        domains = [norm_domain(d) for v in trailer_values(body, 'SA-Current-Checkpoint') for d in v.split(',')]
        if 'all' in domains and not is_wip(body):
            return sha
    return git(root, 'log', '-1', '--format=%H', '--', f'{DIR}/current.md') or None


def domain_sources(root):
    res, domain, collecting = {}, None, False
    for line in (read(pdir(root) / 'current.md') or '').splitlines():
        s = line.strip()
        if s.startswith('#'):
            collecting = False
            if re.match(r'^#{3} ', s):
                domain = norm_domain(s.lstrip('#'))
            continue
        m = re.match(r'^[*_]*sources[*_:]*\s*(.*)$', s, re.I)
        if m:
            collecting, globs = True, re.findall(r'`([^`]+)`', m.group(1))
        elif collecting and s.startswith('- '):
            globs = re.findall(r'`([^`]+)`', s)
        else:
            collecting, globs = (collecting and not s), []
        if domain and globs:
            res.setdefault(domain, []).extend(globs)
    return res


def staleness(root, base):
    if not base:
        return {}, []
    srcs = domain_sources(root)
    bases = {}
    for sha, body in git_records(root, 'SA-Current-Checkpoint:'):
        if is_wip(body):
            continue
        for val in trailer_values(body, 'SA-Current-Checkpoint'):
            for domain in (norm_domain(d) for d in val.split(',')):
                for d in (srcs if domain == 'all' else [domain]):
                    bases.setdefault(d, sha)
    deltas = {}
    for checkpoint in {base, *bases.values()}:
        deltas[checkpoint] = [p for p in (git_paths(root, 'diff', '--name-only', f'{checkpoint}..HEAD') or [])
                              if not p.startswith(DIR + '/')]
    stale = {}
    for d, globs in srcs.items():
        hit = [p for p in deltas[bases.get(d, base)] if any(matches(p, g) for g in globs)]
        if hit:
            stale[d] = hit
    # Unmapped = outside every Sources glob and Map path, changed since the newest reconciliation of any scope.
    newest = next((sha for sha, body in git_records(root, 'SA-Current-Checkpoint:') if not is_wip(body)), base)
    if newest not in deltas:
        deltas[newest] = [p for p in (git_paths(root, 'diff', '--name-only', f'{newest}..HEAD') or [])
                          if not p.startswith(DIR + '/')]
    mapped = [g for gl in srcs.values() for g in gl] + map_paths(root)
    unmapped = [p for p in deltas[newest] if not any(matches(p, g) for g in mapped)]
    return stale, unmapped


def map_paths(root):
    """Backticked paths listed under ## Map in current.md."""
    lines = sections(read(pdir(root) / 'current.md') or '').get('map', [])
    return [m.group(1) for line in lines if (m := re.match(r'^\s*- `([^`]+)`', line))]


def merge_op(root):
    gd = git(root, 'rev-parse', '--git-dir')
    if not gd:
        return None
    gd = Path(gd) if Path(gd).is_absolute() else Path(root) / gd
    for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
        if (gd / marker).exists():
            return marker[:-5].lower()
    if (gd / 'rebase-merge').is_dir() or (gd / 'rebase-apply').is_dir():
        return 'rebase'
    return None


def dirty_paths(root):
    out = git(root, 'status', '--porcelain', '-z', '-uall')
    if out is None:
        return []
    paths, entries, i = [], out.split('\0'), 0
    while i < len(entries):
        e = entries[i]
        if len(e) > 3:
            paths.append(e[3:])
            if e[0] in 'RC':
                i += 1
        i += 1
    return paths


def product_status(root):
    m = re.search(r'^Status:\s*(DRAFT|CONFIRMED)\b', read(pdir(root) / 'product.md') or '', re.M | re.I)
    return m.group(1).upper() if m else 'UNSET'


def detect_commands(root):
    root, cmds = Path(root), {}
    pkg = root / 'package.json'
    if pkg.exists():
        try:
            scripts = json.loads(read(pkg) or '{}').get('scripts', {})
        except ValueError:
            scripts = {}
        runner = ('pnpm' if (root / 'pnpm-lock.yaml').exists() else 'yarn' if (root / 'yarn.lock').exists()
                  else 'npm')
        for k in ('test', 'lint', 'build', 'typecheck'):
            if k in scripts:
                cmds.setdefault(k, f'{runner} run {k}')
    if (root / 'pubspec.yaml').exists():
        flutter = re.search(r'^\s*(?:sdk:\s*)?flutter\b', read(root / 'pubspec.yaml') or '', re.M) is not None
        cmds.setdefault('test', 'flutter test' if flutter else 'dart test')
        cmds.setdefault('lint', 'flutter analyze' if flutter else 'dart analyze')
    pyproject = read(root / 'pyproject.toml') or ''
    if pyproject or any((root / f).exists() for f in ('pytest.ini', 'setup.cfg', 'tox.ini', 'setup.py')):
        cmds.setdefault('test', 'python -m pytest -q')
        if 'ruff' in pyproject:
            cmds.setdefault('lint', 'ruff check .')
    for marker, test, build in (('Cargo.toml', 'cargo test', 'cargo build'),
                                ('go.mod', 'go test ./...', 'go build ./...'),
                                ('build.gradle', './gradlew test', './gradlew build'),
                                ('build.gradle.kts', './gradlew test', './gradlew build')):
        if (root / marker).exists():
            cmds.setdefault('test', test)
            cmds.setdefault('build', build)
    if list(root.glob('*.sln')) or list(root.glob('*.csproj')):
        cmds.setdefault('test', 'dotnet test')
        cmds.setdefault('build', 'dotnet build')
    return cmds


# ── commands ─────────────────────────────────────────────────────────────

def boot(root):
    foreign = [f'{n} ({LEGACY_MARKERS[n][0]})' for n in legacy_found(root)]
    if foreign and not plan_exists(root):
        return 0, ['STATE: LEGACY', 'FOREIGN STATE: ' + ', '.join(foreign),
                   'NEXT: Another planning/state system lives here. `legacy` (preview), extract its goal, decisions, '
                   'current state and open work into a new plan (references/plan.md §6 adoption), `validate`, then '
                   '`legacy --apply`. Small unrelated request -> do it, but report the foreign state.']
    if not plan_exists(root):
        return 0, ['STATE: NO_PLAN',
                   'NEXT: Multi-session work, a new product or a plan request -> Genesis (`map`, then `init`, '
                   'references/plan.md). Small request -> just do it.']
    git_ok = has_git(root)
    all_tasks = list_tasks(root)
    tasks = [t for t in all_tasks if t['status'] != 'DONE' or not t['evidence']]
    open_ids = {t['id'] for t in tasks}
    cfg = load_config(root)
    notes, state, out = [], None, []
    if foreign:
        notes.append('foreign state still present: ' + ', '.join(foreign) +
                     ' -> check its open work is in the plan, then `legacy --apply`')
    bad = [t['id'] for t in tasks if t['status'] == '?']
    ip = [t for t in tasks if t['status'] == 'IN_PROGRESS']
    kept = [t['id'] for t in all_tasks if t['status'] == 'DONE']
    if bad:
        notes.append(f"no valid Status line: {', '.join(bad)} (run `validate`)")
    if len(ip) > 1:
        notes.append(f"several IN_PROGRESS: {', '.join(t['id'] for t in ip)}: keep one, set the rest READY")
    if kept:
        notes.append(f"finished task files still present: {', '.join(kept)}: delete after their checkpoint commit")
    active = ip[0] if ip else None
    pending = [(t['id'], e) for t in tasks for e in t['external'] if e['state'] in ('sent', 'response_unknown')]
    review = [t for t in tasks if t['status'] == 'REVIEW']
    local_done = {t['id'] for t in all_tasks if t['status'] == 'DONE' and t['evidence']}
    done, stale, unmapped, recent, since_audit = set(local_done), {}, [], [], 0
    if not git_ok:
        state = 'NO_GIT'
        gitline = 'git: none (degraded: no checkpoints, no history; never `git init` unasked)'
    else:
        branch = git(root, 'symbolic-ref', '--short', '-q', 'HEAD')
        head = git(root, 'rev-parse', '--short', 'HEAD') or '(no commits)'
        if not branch:
            notes.append('detached HEAD: do not commit until a branch exists (edge-cases: Detached HEAD)')
        if git(root, 'rev-parse', '--is-shallow-repository') == 'true':
            notes.append('shallow clone: missing history proves nothing (edge-cases: Shallow)')
        base = checkpoint_base(root)
        dirty = dirty_paths(root)
        plan_dirty = [p for p in dirty if p.startswith(DIR + '/')]
        other = [p for p in dirty if not p.startswith(DIR + '/')]
        owned = [p for p in other if active and any(matches(p, a) for a in active['areas'])]
        unowned = [p for p in other if p not in owned]
        _, completed = history_task_ids(root)
        done = (completed | local_done) - open_ids
        stale, unmapped = staleness(root, base)
        recent = recent_closed(root, open_ids)
        since_audit = closed_since_audit(root, open_ids)
        op = merge_op(root)
        # INTERRUPTED = the active task left uncommitted work; a clean IN_PROGRESS task simply resumes.
        state = ('CONFLICTED' if op else 'READBACK_FIRST' if pending else 'DIRTY' if unowned
                 else 'INTERRUPTED' if active and owned else 'ADVANCED' if stale or unmapped else 'RESUME')
        if active and state in ('DIRTY', 'ADVANCED'):
            notes.append(f"{active['id']} is IN_PROGRESS (owner {active['owner'] or '?'}): resume it after this")
        gitline = f"git: {branch or 'DETACHED'} @ {head} | dirty {len(other)} (+{len(plan_dirty)} plan)"
        if op:
            notes.append(f'{op} in progress')
        if unowned:
            notes.append('dirty outside active task: ' + ', '.join(unowned[:8]) + (' ...' if len(unowned) > 8 else ''))
        if plan_dirty and not active:
            notes.append('uncommitted .store-automation edits: review and commit them')
        if not base:
            notes.append('no checkpoint commit yet: the next plan commit carries SA trailers')
        if not git(root, 'remote'):
            notes.append('no git remote: commits are local only, not durable for other machines (edge-cases: Push failure)')
        elif branch:
            ahead = git(root, 'rev-list', '--count', '@{u}..HEAD')
            if ahead is None:
                notes.append(f'branch {branch} has no upstream: `git push -u <remote> {branch}` per git.push')
            elif ahead != '0':
                notes.append(f'{ahead} commit(s) not pushed' +
                             (': push now (git.push auto)' if cfg.get('git', {}).get('push', 'auto') == 'auto' else ''))
    if git_ok is False and pending:
        state = 'READBACK_FIRST'
    out += [f'STATE: {state}', gitline] + [f'  ! {n}' for n in notes]
    pstat = product_status(root)
    out.append(f'PRODUCT: {pstat}' + {'DRAFT': ' (goal not confirmed: plan only goal-independent work; ask the user)',
                                      'UNSET': ' (add `Status: DRAFT|CONFIRMED` to product.md)'}.get(pstat, ''))
    for tid, e in pending:
        out.append(f"EXTERNAL {tid}: {e['op']} is {e['state']} -> readback first: {e['readback']} (never resend before it)")
    # A BLOCKED review waits for a fixer, not for another review.
    fix = [t for t in review if (v := re.findall(r'^- review by (.+?) \| (PASS|BLOCKED) \|', '\n'.join(t['review']),
                                                re.M)) and v[-1][1] == 'BLOCKED']
    review = [t for t in review if t not in fix]
    for t in fix:
        out.append(f"FIX: {t['id']} (review BLOCKED; owner {t['owner'] or '?'}) -> an implementer runs "
                   f"`start {t['id']} --takeover \"fix review\"`, fixes the findings, checks; a non-implementer re-reviews")
    if review:
        out.append('REVIEW: ' + ', '.join(f"{t['id']} (owner {t['owner'] or '?'})" for t in review) +
                   ' -> a different, stronger agent that did not implement it reviews these before new implementation')
    waiting = [t for t in tasks if t['status'] == 'BLOCKED' and t['blocked'].lower().startswith('user')]
    if waiting:
        out.append('QUESTIONS (ask the user when present): ' +
                   '; '.join(f"{t['id']}: {t['blocked']}" for t in waiting))
    out.append(f'PLAN: {len(tasks)} open, {len(done)} done')
    for t in tasks[:BUDGETS['open_tasks']]:
        extra = []
        od = [d for d in t['deps'] if d in open_ids]
        if od:
            extra.append('deps ' + ','.join(od))
        if t['status'] == 'BLOCKED' and t['blocked']:
            extra.append(t['blocked'][:50])
        mark = '>' if t is active else ' '
        out.append(f" {mark} {t['id']} {t['status']:<11} {t['priority']} {t['tier'] or '-'} "
                   f"{t['milestone'] or '-'} {t['title'][:60]}{'  [' + '; '.join(extra) + ']' if extra else ''}")
    if len(tasks) > BUDGETS['open_tasks']:
        out.append(f"   ... {len(tasks) - BUDGETS['open_tasks']} more")
    ready = sorted((t for t in tasks if t['status'] == 'READY' and set(t['deps']) <= done),
                   key=lambda t: (t['priority'], int(t['id'][3:])))
    promote = [t['id'] for t in tasks if t['status'] == 'PLANNED' and set(t['deps']) <= done]
    for t in tasks:
        unresolved = set(t['deps']) - open_ids - done
        if unresolved:
            out.append(f"  ! {t['id']}: dependencies without completion evidence: {', '.join(sorted(unresolved))}")
    focus = active or (ready[0] if ready else None)
    if focus:
        out.append(f"FOCUS {focus['id']} ({focus['status']}, {focus['priority']}, tier {focus['tier'] or '?'}, "
                   f"risk {focus['risk'] or '?'}, owner {focus['owner'] or '-'}): "
                   f"{len(focus['open_items'])}/{len(focus['items'])} acceptance open")
        if focus['next']:
            out.append(f"  next: {focus['next']}")
        for item in focus['open_items'][:5]:
            out.append(f"  - [ ] [{item['kind'] or '?'}] {item['text']}  (criterion {item['id']})")
        missing = [n for n, ok in (('Steps', focus['steps']), ('Acceptance', focus['items']),
                                   ('Verify command', focus['verify'])) if not ok]
        if missing:
            out.append(f"  ! {focus['id']} is not an executable spec (missing {', '.join(missing)}): write them first")
        if focus['tier'] == 'H':
            out.append('  ! tier H: design/spec/review work; a weaker model refines specs or stops here')
    if promote:
        out.append(f"  hint: deps done, write full specs and set READY: {', '.join(promote)}")
    if since_audit >= 5:
        out.append(f'  hint: {since_audit} tasks closed since the last plan audit -> Plan audit (references/plan.md)')
    if recent:
        out.append('RECENT: ' + '; '.join(f'{ids} by {agent} ({sha})' for ids, agent, sha in recent))
        if drift := committed_drift(root):
            out.append(f'  ! {drift[0]} ({drift[1]}): committed Areas differ from what `accept` verified (a hook '
                       'rewrote files, or files were left uncommitted) -> verify that commit; fix in a new task')
    for d, files in stale.items():
        out.append(f"STALE {d}: {', '.join(files[:5])}{' ...' if len(files) > 5 else ''}")
    if unmapped:
        out.append(f"UNMAPPED: {', '.join(unmapped[:8])}{' ...' if len(unmapped) > 8 else ''}")
    load = [focus['file']] if focus else []
    load.append(pdir(root) / 'current.md')
    if focus:
        for n in sorted(set(re.findall(r'ADR-(\d+)', focus['text']))):
            load += sorted((pdir(root) / 'decisions').glob(f'ADR-{int(n):03d}*.md'))
    load += [p for p in (pdir(root) / 'product.md', pdir(root) / 'constraints.md') if p.exists()]
    out.append('LOAD: ' + ' '.join(Path(os.path.relpath(p, root)).as_posix() for p in load))
    cmds = {k: v for k, v in cfg.get('commands', {}).items() if v}
    if cmds:
        out.append('CMDS: ' + ' | '.join(f'{k}={v}' for k, v in cmds.items()))
    g = cfg.get('git', {})
    out.append(f"MODE: commit={g.get('commit', 'auto')} push={g.get('push', 'auto')}")
    nxt = {
        'CONFLICTED': 'Finish the Git operation first (edge-cases: Conflicts). Start no task.',
        'READBACK_FIRST': 'Read back every listed external operation with the existing tool, record the observed '
                          'state in the task External line, then continue. Never resend first.',
        'DIRTY': 'Classify each listed path: mine/user/generated/unknown. Never reset/clean/stash/checkout unknown '
                 'work. Continue only on non-overlapping files.',
        'INTERRUPTED': f"Resume {active['id'] if active else ''}: compare `git diff --stat` with its Resume notes, "
                       'then continue at the first open acceptance item.',
        'ADVANCED': 'Inspect relevant STALE/UNMAPPED files and reconcile current.md before checkpointing.',
    }.get(state)
    if not nxt:
        if review:
            nxt = f"Strong model: `review` {review[0]['id']}. Weaker model: continue with tier L/M work below."
        elif fix:
            nxt = f"Fix {fix[0]['id']}: read its Review findings, `start --takeover \"fix review\"`, fix, `check`."
        elif active:
            nxt = (f"Continue {active['id']} from its Resume; if you are not its Owner and it stopped, "
                   f"`start {active['id']} --takeover \"<reason>\"`.")
        elif focus:
            nxt = f"Route the user's request first. Authorized 'continue': `start {focus['id']}` and work the queue."
        elif promote:
            nxt = f'Refine {promote[0]} to an executable spec, set READY and start it.'
        elif tasks and all(t['status'] == 'BLOCKED' for t in tasks):
            nxt = 'Every open task is BLOCKED: report blockers to the user and stop.'
        elif tasks:
            nxt = 'No startable task: fix statuses (`validate`) or refine a PLANNED task to READY.'
        else:
            nxt = "Queue empty: handle the user's message, or run the Final audit (references/plan.md)."
    out.append(f'NEXT: {nxt}')
    return 0, out


def map_repo(root):
    git_ok = has_git(root)
    files = repo_files(root, git_ok)
    out = [f"FILES: {len(files)}{' (git ls-files, ignored excluded)' if git_ok else ''}", 'TREE (files per dir):']
    tops, subs, exts = {}, {}, {}
    for f in files:
        parts = f.split('/')
        if len(parts) > 1:
            tops[parts[0]] = tops.get(parts[0], 0) + 1
            if len(parts) > 2:
                key = f'{parts[0]}/{parts[1]}'
                subs[key] = subs.get(key, 0) + 1
        ext = os.path.splitext(f)[1].lower()
        if ext:
            exts[ext] = exts.get(ext, 0) + 1
    for top, n in sorted(tops.items(), key=lambda x: -x[1])[:25]:
        out.append(f'  {top}/ {n}')
        kids = sorted(((k, v) for k, v in subs.items() if k.startswith(top + '/')), key=lambda x: -x[1])
        out += [f'    {k}/ {v}' for k, v in kids[:8]]
        if len(kids) > 8:
            out.append(f'    ... {len(kids) - 8} more dirs')
    root_files = sorted(f for f in files if '/' not in f)
    out.append('ROOT FILES: ' + ' '.join(root_files[:40]) + (' ...' if len(root_files) > 40 else ''))
    out.append('EXTENSIONS: ' + ' '.join(f'{e}:{n}' for e, n in sorted(exts.items(), key=lambda x: -x[1])[:12]))
    docs = [f for f in files if f.split('/')[-1].upper() in
            ('README.MD', 'AGENTS.MD', 'CLAUDE.MD', 'GEMINI.MD', 'CONTRIBUTING.MD', 'ARCHITECTURE.MD')]
    if docs:
        out.append('INSTRUCTION/DOC FILES: ' + ' '.join(docs[:15]))
    for marker in legacy_found(root):
        out.append(f'FOREIGN STATE: {marker} ({LEGACY_MARKERS[marker][0]}) -> extract into the plan, then `legacy --apply`')
    cmds = detect_commands(root)
    out.append('CMDS: ' + (' | '.join(f'{k}={v}' for k, v in cmds.items()) if cmds else 'none detected'))
    out.append('NEXT: Read only manifests, entry points and instruction files (<=15 files), then `init`.')
    return 0, out


def write_new(path, content, created):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8', newline='\n') as f:
            f.write(content)
        created.append(path)


def ensure_pointers(root):
    """Agent-neutral activation: AGENTS.md always; CLAUDE.md/GEMINI.md only when they already exist."""
    done = []
    for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):
        path, text = Path(root) / name, read(Path(root) / name)
        if text is None and name != 'AGENTS.md':
            continue
        if text is None:
            with path.open('x', encoding='utf-8', newline='\n') as f:
                f.write(POINTER)
            done.append((name, 'created'))
        elif POINTER_MARK not in text:
            with open(path, 'a', encoding='utf-8', newline='\n') as f:
                f.write(('\n' if text.endswith('\n') else '\n\n') + POINTER)
            done.append((name, 'appended'))
    return done


def init(root):
    p, created = pdir(root), []
    if p.exists() and not p.is_dir():
        raise ValueError(DIR + ' exists and is not a directory')
    if has_git(root) and git(root, 'check-ignore', '-q', f'{DIR}/product.md') is not None:
        return 2, [f'FAIL {DIR}/ is gitignored; the plan must be tracked. Remove that ignore line '
                   f'(keep only {DIR}/runs/ ignored), then run init again.']
    config = {'schema': 1, 'commands': {'test': '', 'lint': '', 'build': '', 'run': '', **detect_commands(root)},
              'git': {'commit': 'auto', 'push': 'auto'}, 'check_timeout': 900}
    write_new(p / 'config.json', json.dumps(config, indent=2, ensure_ascii=False) + '\n', created)
    write_new(p / 'current.md', CURRENT_TMPL, created)
    write_new(p / 'product.md', PRODUCT_TMPL, created)
    write_new(p / 'constraints.md', CONSTRAINTS_TMPL, created)
    write_new(p / '.gitignore', 'runs/\n', created)
    (p / 'tasks').mkdir(exist_ok=True)
    (p / 'decisions').mkdir(exist_ok=True)
    out = [f'CREATED {Path(os.path.relpath(f, root)).as_posix()}' for f in created] or ['EXISTS: nothing overwritten']
    out += [f'POINTER {name} ({action})' for name, action in ensure_pointers(root)]
    out.append('NOTE: config.json commands are detected guesses; run each once and correct it before relying on it.')
    out.append('NEXT: Fill current.md from code, product.md from the user interview (unknown -> Open Decisions), '
               'constraints.md, config.json commands. Then `new` per gap, then the genesis commit.')
    return 0, out


def new_task(root, title, depends='', risk=None, priority=None, tier=None, milestone=''):
    if not plan_exists(root):
        return 3, ['NO_PLAN: run `init` first']
    tdir = pdir(root) / 'tasks'
    tdir.mkdir(exist_ok=True)
    nums = [int(TASK_FILE_RE.match(f.name).group(1)) for f in tdir.iterdir() if TASK_FILE_RE.match(f.name)]
    every, _ = history_task_ids(root)
    # Every local branch and worktree too: two branches must not both mint SA-014 (a fetch brings remote ones).
    names = git(root, 'log', '--all', '--format=%B', '--name-only', '--', f'{DIR}/tasks') or ''
    every.update(norm_id(n) for n in re.findall(r'(?:^|/|\s)SA-(\d+)\b', names))
    nums += [int(i[3:]) for i in every]
    tid = norm_id(max(nums, default=0) + 1)
    deps = [norm_id(n) for n in re.findall(r'SA-(\d+)', depends or '')]
    path = tdir / f'{tid}.md'
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(TASK_TMPL.format(id=tid, title=title, risk=risk or 'MEDIUM', priority=priority or 'P2',
                                 tier=tier or 'M', milestone=milestone or '-', deps=', '.join(deps) or '-'))
    return 0, [f'CREATED {Path(os.path.relpath(path, root)).as_posix()} (PLANNED)',
               'NEXT: Write it for a weaker model (references/plan.md): Objective in the user\'s words, Areas, '
               'numbered Steps with exact paths, typed Acceptance checkboxes, Verify commands; then Status: READY.']


def start(root, task_id, owner, takeover=''):
    """READY -> IN_PROGRESS. Taking over another owner's IN_PROGRESS/REVIEW task needs a recorded reason."""
    owner = agent_id(owner, '--owner')
    with checkout_lock(pdir(root)):
        task = find_task(root, task_id)  # read the file inside the lock: it may have changed while waiting
        all_tasks = list_tasks(root)
        others = [t['id'] for t in all_tasks if t['status'] == 'IN_PROGRESS' and t['id'] != task['id']]
        if others:
            return 2, [f"FAIL {', '.join(others)} already IN_PROGRESS: finish it, or write Resume and set it "
                       'READY (BLOCKED if it waits for the user)']
        open_ids = {t['id'] for t in all_tasks}
        done_ids = {t['id'] for t in all_tasks if t['status'] == 'DONE' and t['evidence']}
        if has_git(root):
            _, closed = history_task_ids(root)
            done_ids |= closed
        unresolved = sorted(set(task['deps']) - open_ids - done_ids)
        if unresolved:
            return 2, [f"FAIL {task['id']} depends on {', '.join(unresolved)}: no verified completion evidence"]
        foreign = task['owner'] and task['owner'] != owner and task['status'] in ('IN_PROGRESS', 'REVIEW')
        if task['status'] not in ('READY', 'IN_PROGRESS', 'BLOCKED') and not (task['status'] == 'REVIEW' and takeover):
            return 2, [f"FAIL {task['id']} is {task['status']}: only READY or unblocked tasks start "
                       '(REVIEW needs --takeover to fix a blocking review)']
        if foreign and not takeover.strip():
            return 2, [f"FAIL {task['id']} is owned by {task['owner']}. If that agent is no longer running (no "
                       'recent activity, user confirms, or its session ended), rerun with --takeover "<reason>"']
        missing = [n for n, ok in (('Steps', task['steps']), ('Acceptance', task['items']),
                                   ('Verify', task['verify']), ('Areas', task['areas'])) if not ok]
        if missing:
            return 2, [f"FAIL {task['id']} is not an executable spec: missing {', '.join(missing)}"]
        if task['status'] == 'READY' and not task['ready_by'] and (
                task['risk'] != 'LOW' or any(i['kind'] in SECURE_KINDS for i in task['items'])):
            return 2, [f"FAIL {task['id']} needs a strong model's READY check first: confirm the risk "
                       'classification and that the spec leaves no design choice to the implementer, then '
                       'record `- ready by <model id>: <what you confirmed>` in Notes (B13: a weak model '
                       'must not start risk or outside-contract work on its own judgment)']
        errors = task_errors(task)
        if errors:
            return 2, [f"FAIL {task['id']}"] + [f'  - {e}' for e in errors]
        if foreign:
            append_section(task['file'], 'Notes', f"- takeover from {task['owner']} by {owner}: {takeover.strip()}")
        # Who implemented, at which risk and spec: reviewers are checked against it, risk never drops below it.
        record = {'owner': owner, 'risk': task['risk'], 'contract': contract(task)}
        if record not in start_records(task):
            append_section(task['file'], 'Notes', '- start by {owner} | risk={risk} | contract={contract}'.format(**record))
        headers = {'Status': 'IN_PROGRESS', 'Owner': owner}
        if task['status'] == 'BLOCKED':
            headers['Blocked'] = '-'  # the caller resolved the block
        set_headers(task['file'], headers)  # identity changes in one atomic write
    return 0, [f"STARTED {task['id']} owner={owner} tier={task['tier'] or '?'} risk={task['risk'] or '?'}"
               + (f" (took over from {task['owner']})" if foreign else ''),
               'NEXT: Verify inherited work before trusting it; implement the Steps; `check`; tick Acceptance '
               'only with evidence; then `accept`.']


def changed(root):
    if not has_git(root):
        return 1, ['NO_GIT: cannot compute changes']
    base = checkpoint_base(root)
    if not base:
        return 1, ['NO_CHECKPOINT: reconcile the domains your task touches, then checkpoint']
    stale, unmapped = staleness(root, base)
    if not stale and not unmapped:
        return 0, ['NO_CHANGES: no source changes since the applicable Current checkpoints']
    out = []
    for d, files in stale.items():
        out.append(f'STALE {d} ({len(files)}):')
        out += [f'  {f}' for f in files[:15]]
    if unmapped:
        out.append(f'UNMAPPED ({len(unmapped)}): not covered by any Sources glob')
        out += [f'  {f}' for f in unmapped[:20]]
    out.append('NEXT: Inspect only these files; update the matching current.md sections; checkpoint those domains.')
    return 0, out


def validate(root):
    if not plan_exists(root):
        return 3, ['NO_PLAN']
    p, fails, warns = pdir(root), [], []
    git_ok = has_git(root)
    try:
        load_config(root)
    except ValueError as exc:
        fails.append(str(exc))
    for name, key in (('current.md', 'current'), ('product.md', 'product'), ('constraints.md', 'constraints')):
        text = read(p / name)
        if text is None:
            (fails if name != 'constraints.md' else warns).append(f'{name} missing')
            continue
        if len(text.splitlines()) > BUDGETS[key]:
            warns.append(f'{name}: {len(text.splitlines())} lines > {BUDGETS[key]}')
        if name != 'constraints.md' and has_placeholder(text):
            warns.append(f'{name}: unfilled template placeholders')
    if product_status(root) == 'UNSET':
        warns.append('product.md has no `Status: DRAFT|CONFIRMED` line')
    if git_ok and git(root, 'check-ignore', '-q', f'{DIR}/product.md') is not None:
        fails.append(f'{DIR}/ is gitignored; the plan must be tracked')
    all_tasks = list_tasks(root)
    tasks = [t for t in all_tasks if t['status'] != 'DONE' or not t['evidence']]
    ids = {t['id'] for t in tasks}
    _, completed = history_task_ids(root) if git_ok else (set(), set())
    completed |= {t['id'] for t in all_tasks if t['status'] == 'DONE' and t['evidence']}
    if len(tasks) > BUDGETS['open_tasks']:
        warns.append(f"{len(tasks)} open tasks > {BUDGETS['open_tasks']} (merge or defer distant work)")
    ip = [t['id'] for t in tasks if t['status'] == 'IN_PROGRESS']
    if len(ip) > 1:
        fails.append(f"multiple IN_PROGRESS: {', '.join(ip)}")
    adrs = {int(ADR_FILE_RE.match(f.name).group(1)) for f in (p / 'decisions').iterdir()
            if ADR_FILE_RE.match(f.name)} if (p / 'decisions').is_dir() else set()
    for t in all_tasks:
        tid = t['id']
        fails.extend(task_errors(t))
        if t['status_note']:
            warns.append(f'{tid}: notes on the Status line; move them to Blocked:/Notes/Resume')
        if t['status'] == 'DONE' and not t['evidence']:
            fails.append(f'{tid}: DONE without Evidence')
        if t['header_id'] and t['header_id'][0] != tid:
            warns.append(f"{tid}: title says {t['header_id'][0]}")
        # Only spec sections: Resume/Notes prose may mention <id> legitimately.
        parts = sections(t['text'])
        spec = '\n'.join(line for k in ('', 'objective', 'steps', 'acceptance', 'verify') for line in parts.get(k, []))
        if has_placeholder(spec) and t['status'] != 'PLANNED':
            warns.append(f'{tid}: unfilled template placeholders')
        if t['priority_raw'] and t['priority_raw'].upper()[:2] not in PRIORITY_VALUES:
            warns.append(f'{tid}: Priority must be P1|P2|P3')
        if t['tier'] not in TIER_VALUES:
            warns.append(f'{tid}: Tier must be L|M|H')
        if t['status'] in ('READY', 'IN_PROGRESS', 'REVIEW') and t['vague']:
            warns.append(f"{tid}: vague words in Steps/Acceptance: {', '.join(t['vague'])}")
        for cmd in t['verify']:
            if re.search(r'[|;&<>]', cmd):
                warns.append(f'{tid}: Verify runs without a shell; split `{cmd}` into plain commands')
        if t['status'] == 'BLOCKED' and not t['blocked']:
            warns.append(f"{tid}: BLOCKED without 'Blocked:' reason")
        if t['lines'] > BUDGETS['task']:
            warns.append(f"{tid}: {t['lines']} lines > {BUDGETS['task']} (split the task)")
        for d in t['deps']:
            if d not in ids and d not in completed:
                warns.append(f'{tid}: depends on {d}, no verified completion evidence')
        for n in set(re.findall(r'ADR-(\d+)', t['text'])):
            if int(n) not in adrs:
                warns.append(f'{tid}: references missing ADR-{n}')
        if t['status'] in ('READY', 'IN_PROGRESS', 'REVIEW') and not t['ready_by'] and (
                t['risk'] != 'LOW' or any(i['kind'] in SECURE_KINDS for i in t['items'])):
            warns.append(f"{tid}: risk or outside-contract Acceptance without a strong model's `ready by <id>:` "
                         'Notes line (references/plan.md READY)')
        if t['status'] == 'DONE':
            continue
        spec_text = '\n'.join(parts.get('objective', []) + parts.get('steps', []) + t['areas'])
        if t['risk'] != 'HIGH' and (hit := HIGH_RISK_RE.search(spec_text)):
            warns.append(f"{tid}: mentions `{hit.group(0)}` but Risk is {t['risk'] or '?'}; auth, persistence, "
                         'migrations, payments and permissions are HIGH (references/plan.md §2)')
        kinds = {i['kind'] for i in t['items']}
        if kinds & {'visual', 'interaction'} and not {'visual', 'interaction', 'accessibility'} <= kinds:
            warns.append(f"{tid}: UI work needs [visual], [interaction] and [accessibility] Acceptance, each "
                         f"observed separately (has {', '.join(sorted(kinds))})")
        for cmd in t['verify']:
            for word in cmd.split()[1:]:
                path = word.split('::')[0].rstrip(',')
                if ('/' in path or re.search(r'\.\w{1,5}$', path)) and (Path(root) / path).is_file() and \
                        not any(matches(path, a) for a in t['areas']):
                    warns.append(f'{tid}: Verify uses `{path}` outside Areas; evidence would not notice it change')
    ra = re.findall(r'^\s*- (RA-\d+)\b', '\n'.join(sections(read(p / 'product.md') or '').get('riskiest assumptions', [])),
                    re.M)
    if ra and all_tasks and not any(ra[0] in t['text'] for t in all_tasks) and not (
            git_ok and git(root, 'log', '-1', '--format=%H', f'-S{ra[0]}', '--', f'{DIR}/tasks')):
        fails.append(f'{ra[0]} (product.md Riskiest Assumptions) is probed by no task: an M1 task names it '
                     '(references/plan.md §6 step 8)')
    for f in sorted((p / 'decisions').glob('ADR-*.md')) if (p / 'decisions').is_dir() else []:
        adr = read(f) or ''
        missing = [h for h in ('Problem', 'Evidence', 'Options', 'Choice', 'Impact')
                   if not re.search(rf'^#+\s*{h}\b', adr, re.M | re.I)]
        if not re.search(r'^Status:\s*(ACCEPTED|SUPERSEDED by ADR-\d+)', adr, re.M):
            missing.insert(0, 'Status: ACCEPTED|SUPERSEDED by ADR-NNN')
        if missing:
            warns.append(f"{f.name}: missing {', '.join(missing)} (references/plan.md §1)")
    adj, seen = {t['id']: [d for d in t['deps'] if d in ids] for t in tasks}, {}

    def cyclic(n):
        seen[n] = 1
        for d in adj[n]:
            if seen.get(d) == 1 or (d not in seen and cyclic(d)):
                return True
        seen[n] = 2
        return False

    if any(n not in seen and cyclic(n) for n in adj):
        fails.append('dependency cycle')
    out = [f'FAIL {f}' for f in fails] + [f'WARN {w}' for w in warns]
    out.append(f"{'OK' if not fails and not warns else 'SUMMARY'}: {len(tasks)} open tasks, {len(adrs)} ADRs, "
               f'{len(fails)} fail, {len(warns)} warn')
    return (2 if fails else 1 if warns else 0), out
