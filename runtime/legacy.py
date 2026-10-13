"""Retire Store Automation 2.x project state.

The old factory left .factory/ and .factory-bootstrap.json plus .gitignore
lines. They move to an archive beside the project (same volume, one rename);
nothing is deleted here and no old receipt becomes new-schema evidence.
Project Brain files belong to the project-brain skill and are untouched.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

from .receipts import append_record, public_path

LEGACY = ('.factory', '.factory-bootstrap.json')


def found(root):
    return [name for name in LEGACY if (Path(root) / name).exists() or (Path(root) / name).is_symlink()]


def legacy(root, apply=False):
    root = Path(root).resolve(strict=True)
    if root.parent == root:
        raise ValueError('Archive needs a parent directory outside the project')
    names = found(root)
    for name in names:
        public_path(root, name)  # refuses linked legacy paths before anything moves
    try:
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--', *LEGACY],
                                 capture_output=True, text=True, timeout=60).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        tracked = []  # not a git checkout or git unavailable
    if tracked:
        raise ValueError('Legacy files are tracked by git; remove them in a reviewed commit: ' + ', '.join(tracked[:5]))
    ignore = root / '.gitignore'
    lines = []
    if ignore.is_file():
        with ignore.open(encoding='utf-8-sig', newline='') as stream:  # keep the file's line endings
            lines = stream.read().splitlines(keepends=True)
    stale = [line for line in lines if line.strip().rstrip('/') == '.factory' or line.strip().startswith('.factory/')]
    kept = [line for line in lines if line not in stale]
    add_entry = not any(line.strip().rstrip('/') == '.store-automation' for line in kept)
    files = [p for name in names for p in ([root / name] if (root / name).is_file() else (root / name).rglob('*'))
             if p.is_file()]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = root.parent / 'store-automation-legacy-archive' / (root.name + '-' + stamp)
    plan = dict(status='LEGACY_FOUND' if names or stale else 'CLEAN', project=str(root), legacy=names,
                files=len(files), bytes=sum(p.stat().st_size for p in files),
                old_handoffs=sorted(p.relative_to(root).as_posix() for p in files if p.name.startswith('handoff'))[-20:],
                gitignore_remove=[line.strip() for line in stale],
                gitignore_add='.store-automation/' if add_entry and (names or stale) else None,
                archive=str(archive) if names else None, applied=False,
                note='Old receipts are history, not evidence. Brain files are kept. '
                     'The archive is outside the project; delete it once nothing needs it.')
    if not apply or plan['status'] == 'CLEAN':
        return plan
    moved = []
    if names:
        archive.mkdir(parents=True)
        try:
            for name in names:
                # Same-volume rename: an open file or running process inside aborts it.
                os.rename(root / name, archive / name)
                moved.append(name)
        except OSError:
            for name in reversed(moved):
                os.rename(archive / name, root / name)
            raise
    if stale or plan['gitignore_add']:
        eol = '\r\n' if any(line.endswith('\r\n') for line in kept) else '\n'
        body = ''.join(kept)
        if plan['gitignore_add']:
            body += ('' if not body or body.endswith('\n') else eol) + '.store-automation/' + eol
        ignore.write_text(body, encoding='utf-8', newline='')
    plan.update(applied=True)
    plan['record'] = append_record(root, 'migration', plan)
    return plan
