"""Retire older project state: Store Automation 2.x and Project Brain schema 4.

2.x left .factory/ and .factory-bootstrap.json. A Project Brain plan is
converted into .store-automation/ (PB-NNN -> SA-NNN). Originals move to an
archive beside the project in one same-volume rename each; nothing is deleted
and no old receipt becomes new evidence. Tracked .project-brain files show up
as deletions for the adoption commit; Git history keeps them.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

from . import plan
from .paths import public_path

LEGACY = ('.factory', '.factory-bootstrap.json', '.project-brain')
BRAIN_POINTER = """<!-- project-brain -->
## Project Brain
This project keeps its state in `.project-brain/` (current architecture, target, open tasks).
Before any work, load the `project-brain` skill and run its boot step; follow it for all work here.
"""
PRODUCT_EXTRA = ('Users', 'Core Journeys', 'Platforms', 'Riskiest Assumptions')


def found(root):
    return [name for name in LEGACY if (Path(root) / name).exists() or (Path(root) / name).is_symlink()]


def _ignore_lines(root):
    ignore = Path(root) / '.gitignore'
    if not ignore.is_file():
        return ignore, []
    with ignore.open(encoding='utf-8-sig', newline='') as stream:  # keep the file's line endings
        return ignore, stream.read().splitlines(keepends=True)


def _brain_config(text):
    """Commands and git policy from a schema-4 Brain config.yaml (two-level scalar subset)."""
    out, section = {'commands': {}, 'git': {}}, None
    for line in text.splitlines():
        if m := re.fullmatch(r'([\w-]+):\s*(.*)', line):
            section = m.group(1) if not m.group(2) else None
        elif (m := re.fullmatch(r'  ([\w-]+):\s*(.*)', line)) and section in out:
            raw = m.group(2).strip()
            out[section][m.group(1)] = json.loads(raw) if raw.startswith('"') else raw.strip("'")
    git_ = {'commit': out['git'].get('commit', 'auto'),
            'push': 'auto' if out['git'].get('push', 'manual') in ('auto', 'always') else 'ask'}
    return {'schema': 1, 'commands': out['commands'], 'git': git_, 'check_timeout': 900}


def _convert_brain(src):
    """{relative path in .store-automation: text} from a schema-4 .project-brain directory."""
    config = plan.read(src / 'config.yaml') or ''
    if not re.search(r'^schema_version:\s*"?4"?\s*$', config, re.M):
        raise ValueError('.project-brain is not schema 4; convert it with Project Brain migrate first')
    files = {'config.json': json.dumps(_brain_config(config), indent=2, ensure_ascii=False) + '\n',
             '.gitignore': 'runs/\n'}
    rename = lambda text: re.sub(r'\bPB-(\d+)', r'SA-\1', text)
    for name in ('current.md', 'constraints.md'):
        if (src / name).is_file():
            files[name] = rename(plan.read(src / name))
    target = plan.read(src / 'target.md') or '# Target\nStatus: DRAFT\n'
    product = re.sub(r'^# .*$', '# Product', rename(target), count=1, flags=re.M)
    for heading in PRODUCT_EXTRA:
        if f'## {heading}' not in product:
            product += f'\n## {heading}\n- UNKNOWN: fill during the adoption interview\n'
    files['product.md'] = product
    for adr in sorted((src / 'decisions').glob('ADR-*.md')) if (src / 'decisions').is_dir() else []:
        files[f'decisions/{adr.name}'] = rename(plan.read(adr))
    tasks = {f.name: plan.read(f) for f in (src / 'tasks').glob('PB-*.md')} if (src / 'tasks').is_dir() else {}
    open_ids = {re.sub(r'^PB-0*(\d+)\.md$', r'\1', n) for n in tasks}
    for name, text in sorted(tasks.items()):
        text = rename(text)
        dropped = []

        def keep_open(m):
            ids = re.findall(r'SA-0*(\d+)', m.group(1))
            dropped.extend(i for i in ids if i not in open_ids)
            kept = [plan.norm_id(i) for i in ids if i in open_ids]
            return 'Depends: ' + (', '.join(kept) or '-')
        text = re.sub(r'^Depends:\s*(.*)$', keep_open, text, count=1, flags=re.M)
        if dropped:
            text = text.rstrip('\n') + '\n' + ''.join(
                f'- migrated: closed dependency PB-{int(i):03d} removed (completed in Project Brain history)\n'
                for i in dropped)
        files['tasks/' + name.replace('PB-', 'SA-')] = text
    return files


def legacy(root, apply=False):
    root = Path(root).resolve(strict=True)
    if root.parent == root:
        raise ValueError('Archive needs a parent directory outside the project')
    names = found(root)
    for name in names:
        public_path(root, name)  # refuses linked legacy paths before anything moves
    try:
        tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--', '.factory', '.factory-bootstrap.json'],
                                 capture_output=True, text=True, timeout=60).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        tracked = []  # not a git checkout or git unavailable
    if tracked:
        raise ValueError('2.x files are tracked by git; remove them in a reviewed commit: ' + ', '.join(tracked[:5]))
    converted = {}
    if '.project-brain' in names:
        if plan.plan_exists(root):
            raise ValueError('Both .project-brain and a .store-automation plan exist; reconcile them by hand')
        converted = _convert_brain(root / '.project-brain')
    ignore, lines = _ignore_lines(root)
    stale = [line for line in lines if line.strip().rstrip('/') in ('.factory', '.store-automation')
             or line.strip().startswith('.factory/')]
    kept = [line for line in lines if line not in stale]
    files = [p for name in names for p in ([root / name] if (root / name).is_file() else (root / name).rglob('*'))
             if p.is_file()]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = root.parent / 'store-automation-legacy-archive' / (root.name + '-' + stamp)
    agents = plan.read(root / 'AGENTS.md') or ''
    result = dict(status='LEGACY_FOUND' if names or stale else 'CLEAN', project=str(root), legacy=names,
                  files=len(files), bytes=sum(p.stat().st_size for p in files),
                  old_handoffs=sorted(p.relative_to(root).as_posix() for p in files
                                      if p.name.startswith('handoff'))[-20:],
                  converted=sorted(converted), gitignore_remove=[line.strip() for line in stale],
                  agents_pointer='replace' if BRAIN_POINTER in agents else None,
                  archive=str(archive) if names else None, applied=False,
                  note='Old receipts are history, not evidence. Untagged acceptance items in converted tasks '
                       'fail `validate` until a strong model adds kind tags. The archive is outside the '
                       'project; delete it once nothing needs it.')
    if not apply or result['status'] == 'CLEAN':
        return result
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
    for rel, text in converted.items():
        path = plan.pdir(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    if stale:
        eol = '\r\n' if any(line.endswith('\r\n') for line in kept) else '\n'
        body = ''.join(kept)
        ignore.write_text(body + ('' if not body or body.endswith('\n') else eol), encoding='utf-8', newline='')
    if result['agents_pointer']:
        plan.write_atomic(root / 'AGENTS.md', agents.replace(BRAIN_POINTER, plan.POINTER))
    result['applied'] = True
    result['next'] = ('Commit the adoption (archive is outside the repo), then `boot`; tag acceptance kinds and '
                      'fill product.md gaps.' if converted else '`map` then `init` when planning is needed.')
    return result
