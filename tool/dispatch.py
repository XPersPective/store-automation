"""Immutable attempts and exclusive bucket admission; Brain remains the task store."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import uuid
import ctypes

try:
    from . import sessions, subscriptions
except ImportError:
    import sessions, subscriptions


def absent(pid):
    """Prove absence, rather than treating denied process inspection as death."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == 'nt':
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if handle:
            kernel.CloseHandle(handle)
            return False
        return ctypes.get_last_error() == 87
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def reconcile_team(project):
    """Windows JobObject owns children; release only after every recorded PID is absent."""
    path = owned_path(project, '.factory/team.lock')
    if not path.exists():
        return
    if os.name != 'nt':
        raise sessions.ContainmentError('Native parent-death containment not verified on this platform')
    value = json.loads(path.read_text())
    if not absent(value.get('pid')):
        raise sessions.ContainmentError('Existing controller still alive or inspection unavailable')
    state = json.loads(owned_path(project, '.factory/runs/team-controller.json').read_text())
    if state.get('owner') != value.get('owner') or state.get('project') != str(Path(project).resolve()):
        raise sessions.ContainmentError('Controller ownership record mismatch')
    for row in state.get('agents', []):
        attempt = owned_path(project, '.factory/runs/assignment-' + row['id'] + '.json')
        record = json.loads(attempt.read_text())
        if record.get('pid') and not absent(record['pid']):
            raise sessions.ContainmentError('Owned worker still alive or inspection unavailable')
    state.update(state='RECONCILED_AFTER_EXIT', reconciled_at=time.time())
    atomic(owned_path(project, '.factory/runs/reconciled-' + uuid.uuid4().hex + '.json'), state)
    if json.loads(path.read_text()).get('owner') == value['owner']:
        path.unlink()


def owned_path(project, relative):
    project = Path(project).resolve(strict=True)
    path = project / relative
    if path.is_absolute() and project not in path.parents:
        raise ValueError('Control path escapes project')
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (path, *path.parents) if p != project and project in p.parents):
        raise ValueError('Linked control path refused')
    if project not in path.resolve().parents:
        raise ValueError('Control path escapes project')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def atomic(path, value):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
        temp = Path(stream.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def assignment(project, task, selected, contract_hash, parent=None, surface='stream'):
    risk = task.get('risk', 'HIGH')
    complexity = task.get('complexity', 'COMPLEX')
    floor = max({'SIMPLE': 0, 'STANDARD': 1, 'COMPLEX': 2, 'SPECIALIZED': 2}[complexity],
                {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}[risk])
    if selected.get('quality_tier', -1) < floor:
        raise ValueError('Selected model is below task risk/complexity quality floor')
    if subscriptions.reserve_decision('worker', selected.get('remaining_fraction')) != 'READY':
        raise ValueError('Assignment requires fresh eligible quota')
    record = {'schema_version': 1, 'attempt': uuid.uuid4().hex, 'project': str(Path(project).resolve()),
              'task': task['task_id'], 'contract_sha256': contract_hash,
              'role': task['persona']['role'], 'parent': parent, 'selected': selected,
              'risk': risk, 'complexity': complexity, 'surface': surface,
              'permission': 'source-snapshots-only', 'requested_write': task['permissions'].get('write', False),
              'context_budget_chars': task['delegation']['context_budget_chars'],
              'output_budget_tokens': task['delegation']['output_budget_tokens'], 'output_limit': 'SOFT',
              'reason': task['delegation']['reason'], 'state': 'PREPARED', 'created_at': time.time(),
              'controller_pid': os.getpid(), 'controller_identity': sessions.process_identity(os.getpid())}
    path = owned_path(project, '.factory/runs/assignment-' + record['attempt'] + '.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return path, record


def required_complexity(task):
    complexity = task.get('complexity', 'COMPLEX')
    floor = {'LOW': 'SIMPLE', 'MEDIUM': 'STANDARD', 'HIGH': 'COMPLEX'}[task.get('risk', 'HIGH')]
    order = {'SIMPLE': 0, 'STANDARD': 1, 'COMPLEX': 2, 'SPECIALIZED': 3}
    return complexity if order[complexity] >= order[floor] else floor


@contextmanager
def admit(selected, project, attempt, directory=None):
    # ponytail: native percentages cannot be converted to tokens; one outstanding job per shared bucket.
    directory = Path(directory or Path.home() / '.local/share/store-automation/admission')
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (directory, *directory.parents)):
        raise ValueError('Linked admission directory refused')
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((selected['provider'] + ':' + selected['quota_group']).encode()).hexdigest()
    path = directory / (key + '.lock')
    if path.exists():
        previous = json.loads(path.read_text())
        if absent(previous.get('pid')) and os.name == 'nt':
            # A dead Windows owner closes its kill-on-close JobObjects before admission resumes.
            if json.loads(path.read_text()).get('nonce') == previous.get('nonce'):
                path.unlink()
    nonce = uuid.uuid4().hex
    value = {'nonce': nonce, 'pid': os.getpid(), 'identity': sessions.process_identity(os.getpid()),
             'project': str(Path(project).resolve()), 'attempt': attempt, 'created_at': time.time()}
    try:
        stream = path.open('x', encoding='utf-8')
    except FileExistsError:
        raise RuntimeError('Shared bucket already admitted; inspect owned process before reconciling stale lock')
    release = True
    try:
        with stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        yield
    except sessions.ContainmentError:
        release = False
        raise
    finally:
        if release and path.exists() and json.loads(path.read_text())['nonce'] == nonce:
            path.unlink()


def checked_report(result, task, selected):
    report = result.get('task_result') or {}
    if not subscriptions.report_valid(report, task['task_id']):
        return {'status': 'UNVERIFIED', 'reason': 'Missing or invalid mandatory task report'}
    if any(report[key] != selected[key] for key in ('provider', 'model', 'effort')):
        return {'status': 'UNVERIFIED', 'reason': 'Agent report differs from actual selected route'}
    if report['role'] != task['persona']['role']:
        return {'status': 'UNVERIFIED', 'reason': 'Agent report differs from assigned responsibility'}
    return report


def handoff(project, task, contract_hash, attempt_paths, next_action, brain_output, git_status):
    if not isinstance(next_action, str) or not next_action.strip() or len(next_action) > 1000:
        raise ValueError('Bounded concrete next action required')
    refs = []
    for name in attempt_paths:
        path = Path(name).absolute()
        relative = path.relative_to(Path(project).resolve()).as_posix()
        checked = owned_path(project, relative)
        if not relative.startswith('.factory/runs/') or not checked.is_file() or checked.stat().st_size > 1_000_000:
            raise ValueError('Handoff attempt must be a bounded owned record')
        refs.append({'path': relative, 'sha256': hashlib.sha256(checked.read_bytes()).hexdigest()})
    evidence = owned_path(project, '.factory/runs/handoff-evidence-' + uuid.uuid4().hex + '.json')
    atomic(evidence, {'brain': brain_output, 'git_status': git_status})
    payload = {'schema_version': 1, 'project': str(Path(project).resolve()), 'task': task,
               'contract_sha256': contract_hash, 'attempts': refs, 'next_action': next_action,
               'brain_summary': brain_output[:6000], 'git_status': git_status[:2000],
               'summary_shortened': len(brain_output) > 6000 or len(git_status) > 2000,
               'full_state': {'path': evidence.relative_to(Path(project).resolve()).as_posix(),
                              'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()},
               'created_at': time.time(), 'acceptance': 'UNVERIFIED', 'first_unchecked': 'canonical Brain Acceptance'}
    if len(json.dumps(payload)) > 12000:
        raise ValueError('Handoff summary exceeds budget; retain large evidence by reference')
    path = owned_path(project, '.factory/runs/handoff-' + uuid.uuid4().hex + '.json')
    atomic(path, payload)
    return path
