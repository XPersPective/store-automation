"""Retire foreign planning/state systems after their content lives in the plan.

Any agent or tool may have left its own memory in a project: Project Brain,
Task Master, a Cline memory bank, Kiro specs, Store Automation 2.x. Their
formats differ, so a strong model extracts goal, decisions, current state and
open work into .store-automation/ (plan.md §6) and this module only does the
mechanical part: find, refuse removal before extraction, move everything out
in same-volume renames, drop ignore lines and pointers, and finally delete
the archive once the adoption commit holds the change. Tracked files stay in
Git history; untracked artifacts are gone after --drop-archive.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

from . import plan
from .paths import public_path

# path -> (system, carries plan content that must be extracted first)
MARKERS = {
    '.project-brain': ('Project Brain', True),
    'PROJECT_BRAIN.md': ('Project Brain (single file)', True),
    '.taskmaster': ('Task Master', True),
    'memory-bank': ('Cline memory bank', True),
    '.kiro/specs': ('Kiro specs', True),
    '.factory': ('Store Automation 2.x', False),
    '.factory-bootstrap.json': ('Store Automation 2.x', False),
}
POINTERS = ("""<!-- project-brain -->
## Project Brain
This project keeps its state in `.project-brain/` (current architecture, target, open tasks).
Before any work, load the `project-brain` skill and run its boot step; follow it for all work here.
""",)
INSTRUCTION_FILES = ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md', '.github/copilot-instructions.md', '.cursorrules')
PROTECTED = {'.git', plan.DIR, '.gitignore', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md'}
ARCHIVE_DIR = 'store-automation-legacy-archive'


def found(root):
    return [name for name in MARKERS if (Path(root) / name).exists() or (Path(root) / name).is_symlink()]


def _ignore_lines(root):
    ignore = Path(root) / '.gitignore'
    if not ignore.is_file():
        return ignore, []
    with ignore.open(encoding='utf-8-sig', newline='') as stream:  # keep the file's line endings
        return ignore, stream.read().splitlines(keepends=True)


def _archives(root):
    base = root.parent / ARCHIVE_DIR
    return sorted(base.glob(root.name + '-*')) if base.is_dir() else []


def legacy(root, apply=False, extra=(), drop_archive=False):
    root = Path(root).resolve(strict=True)
    if root.parent == root:
        raise ValueError('Archive needs a parent directory outside the project')
    if drop_archive:
        return _drop(root)
    extra = [e.strip().strip('/') for e in extra if e.strip()]
    for name in extra:
        if name.split('/')[0] in PROTECTED or not (root / name).exists():
            raise ValueError(f'--path {name}: must be an existing foreign state path, not project infrastructure')
    names = found(root) + [e for e in extra if e not in MARKERS]
    for name in names:
        public_path(root, name)  # refuses linked or escaping paths before anything moves
    ignore, lines = _ignore_lines(root)
    def obsolete(line):
        entry = line.strip().rstrip('*').rstrip('/')
        return entry == plan.DIR or any(entry == n or entry.startswith(n + '/') for n in names)
    stale = [line for line in lines if obsolete(line)]
    kept = [line for line in lines if line not in stale]
    files = [p for name in names for p in ([root / name] if (root / name).is_file() else (root / name).rglob('*'))
             if p.is_file()]
    mentions = {}
    for rel in INSTRUCTION_FILES:
        text = plan.read(root / rel) or ''
        hits = [line.strip()[:120] for line in text.splitlines()
                if any(n in line for n in names) or 'project-brain' in line]
        if hits:
            mentions[rel] = hits[:5]
    must_extract = [n for n in names if MARKERS.get(n, ('', True))[1]]
    plan_ok = plan.plan_exists(root) and plan.validate(root)[0] != 2
    archive = root.parent / ARCHIVE_DIR / (root.name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    result = dict(status='LEGACY_FOUND' if names or stale else 'CLEAN', project=str(root),
                  found=[{'path': n, 'system': MARKERS.get(n, ('declared by --path', True))[0]} for n in names],
                  files=len(files), bytes=sum(p.stat().st_size for p in files),
                  extract_first=must_extract, plan_ready=plan_ok,
                  gitignore_remove=[line.strip() for line in stale], instruction_mentions=mentions,
                  archive=str(archive) if names else None, applied=False,
                  next=('Extract goal, decisions, current state, open work, blockers and pending external operations '
                        'into .store-automation (references/plan.md §6, adoption) with a trace of every open item; '
                        '`validate`; then `legacy --apply`.' if must_extract and not plan_ok else
                        '`legacy --apply`, commit the adoption, then `legacy --drop-archive`.'))
    if not apply or result['status'] == 'CLEAN':
        return result
    if must_extract and not plan_ok:
        raise ValueError('Plan content not extracted yet: ' + ', '.join(must_extract) +
                         ' carry goals/tasks; build and validate the .store-automation plan first')
    moved = []
    if names:
        archive.mkdir(parents=True)
        try:
            for name in names:
                (archive / name).parent.mkdir(parents=True, exist_ok=True)
                # Same-volume rename: an open file or running process inside aborts it.
                os.rename(root / name, archive / name)
                moved.append(name)
        except OSError:
            for name in reversed(moved):
                os.rename(archive / name, root / name)
            raise
    if stale:
        eol = '\r\n' if any(line.endswith('\r\n') for line in kept) else '\n'
        body = ''.join(kept)
        ignore.write_text(body + ('' if not body or body.endswith('\n') else eol), encoding='utf-8', newline='')
    for rel in INSTRUCTION_FILES:
        text = plan.read(root / rel)
        if text and any(p in text for p in POINTERS):
            for p in POINTERS:
                text = text.replace(p, plan.POINTER if plan.POINTER_MARK not in text else '')
            plan.write_atomic(root / rel, text)
    result['instruction_mentions'] = {
        rel: hits for rel in INSTRUCTION_FILES
        if (hits := [line.strip()[:120] for line in (plan.read(root / rel) or '').splitlines()
                     if any(n in line for n in names) or 'project-brain' in line][:5])}
    result['applied'] = True
    result['next'] = ('Remove any remaining instruction_mentions by hand, commit the adoption '
                      '(chore(plan): adopt store-automation), then `legacy --drop-archive`.')
    return result


def _drop(root):
    """Delete this project's archives once the removal is committed (tracked content stays in Git history)."""
    archives = _archives(root)
    pending = []
    for archive in archives:
        entries = [p.relative_to(archive).as_posix() for p in archive.iterdir()]
        if plan.has_git(root) and entries:
            status = plan.git(root, 'status', '--porcelain', '--', *entries) or ''
            if status.strip():
                pending.append(archive.name)
    if pending:
        raise ValueError('Commit the adoption first; uncommitted removals for ' + ', '.join(pending))
    for archive in archives:
        shutil.rmtree(archive)
    base = root.parent / ARCHIVE_DIR
    if base.is_dir() and not any(base.iterdir()):
        base.rmdir()
    return {'status': 'DROPPED' if archives else 'NOTHING_TO_DROP', 'project': str(root),
            'deleted': [str(a) for a in archives]}
