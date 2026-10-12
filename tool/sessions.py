"""Owned OpenCode loopback sessions; native attach is the intervention interface.

Caller supplies the same sanitized native environment, including a local server
password, on every command. No provider credentials or chat text are persisted.
"""
import argparse
import base64
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ContainmentError(RuntimeError):
    """Dispatch must stay locked until owned process termination is reconciled."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, url):
        return None


def display_language(value='tr'):
    if value not in ('tr', 'en'):
        raise ValueError('Display language must be tr or en')
    return value


def role_name(role, language='tr'):
    index = 0 if display_language(language) == 'tr' else 1
    role = role if isinstance(role, str) else None
    names = {'factory': ('Yönetici', 'Manager'), 'factory-worker': ('Uygulayıcı', 'Implementer'),
             'factory-reviewer': ('İnceleyen', 'Reviewer'), 'activity': ('Ajan etkinliği', 'Agent activity')}
    aliases = {'supervisor': 'factory', 'orchestrator': 'factory', 'manager': 'factory',
               'worker': 'factory-worker', 'implementer': 'factory-worker', 'reviewer': 'factory-reviewer'}
    known = names.get(aliases.get(role, role))
    return known[index] if known else (role if role and re.fullmatch(r'[\w .-]{1,64}', role) else ('Ajan', 'Agent')[index])


def format_public(data, language=None):
    """Human structural summary only; never render provider conversation/tool bodies."""
    runs = data.get('runs')
    recent_language = runs[0].get('language', 'tr') if isinstance(runs, list) and runs and isinstance(runs[0], dict) else 'tr'
    language = display_language(language or data.get('language') or recent_language)
    index = 0 if language == 'tr' else 1
    def word(tr, en):
        return (tr, en)[index]
    def label(value):
        return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value) else word('bilinmiyor', 'unknown')
    def number(value):
        return str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else word('bilinmiyor', 'unknown')
    states = {'running': ('Çalışıyor', 'Running'), 'busy': ('Çalışıyor', 'Running'),
              'starting': ('Başlıyor', 'Starting'), 'idle': ('Bekliyor', 'Idle'),
              'retry': ('Yeniden deniyor', 'Retrying'), 'pending': ('Beklemede', 'Pending'),
              'completed': ('Tamamlandı', 'Completed'), 'finished': ('Çalıştırma sona erdi', 'Run ended'),
              'failed': ('Başarısız', 'Failed'), 'error': ('Hata', 'Error'),
              'timeout': ('Süre doldu', 'Timed out'), 'interrupted': ('Kesildi', 'Interrupted'),
              'stopped': ('Durduruldu', 'Stopped'), 'watch_closed': ('İzleme kapandı', 'Watch closed'),
              'unchanged': ('Değişmedi', 'Unchanged'), 'native_terminal_opened': ('Yerel oturum açıldı', 'Native session opened')}
    def state(value):
        return states.get(str(value).lower(), ('Bilinmiyor', 'Unknown'))[index]
    def row(item):
        usage = item.get('usage') if isinstance(item.get('usage'), dict) else item.get('reported_usage', {})
        usage = usage if isinstance(usage, dict) else {}
        parts = [role_name(item.get('agent') or item.get('role'), language)]
        if item.get('state') is not None:
            parts.append(state(item['state']))
        if item.get('id') or item.get('session'):
            parts.append(word('Oturum: ', 'Session: ') + label(item.get('id') or item.get('session')))
        native_ids = item.get('native_sessions')
        if isinstance(native_ids, list) and native_ids:
            parts.append(word('Oturumlar: ', 'Sessions: ') + ', '.join(label(value) for value in native_ids))
        if item.get('parent') or item.get('child_session'):
            parts.append(word('Bağlı oturum: ', 'Related session: ') + label(item.get('parent') or item.get('child_session')))
        parts.append(word('Model: ', 'Model: ') + label(item.get('model')))
        tools = item.get('tools') if isinstance(item.get('tools'), list) else []
        latest = item.get('latest') if isinstance(item.get('latest'), dict) else {}
        if not tools and latest.get('tool'):
            tools = [{'tool': latest['tool'], 'state': latest.get('state')}]
        for tool in tools:
            if isinstance(tool, dict):
                parts.append(word('Araç: ', 'Tool: ') + label(tool.get('tool')) + ' (' + state(tool.get('state')) + ')')
        parts.append(word('Token giriş/çıkış: ', 'Tokens in/out: ') + number(usage.get('input')) + '/' + number(usage.get('output')))
        parts.append(word('Kalan kota: bilinmiyor', 'Remaining quota: unknown'))
        if isinstance(item.get('exit_code'), int) and not isinstance(item['exit_code'], bool):
            parts.append(word('Çıkış kodu: ', 'Exit code: ') + str(item['exit_code']))
        if 'classification' in item:
            classifications = {
                'SUCCESS': ('Başarıyla sona erdi', 'Ended successfully'),
                'BLOCKED': ('Engellendi', 'Blocked'), 'QUOTA_EXHAUSTED': ('Kota tükendi', 'Quota exhausted'),
                'RATE_LIMIT': ('İstek sınırı', 'Rate limited'), 'MODEL_UNAVAILABLE': ('Model kullanılamıyor', 'Model unavailable'),
                'TIMEOUT': ('Süre doldu', 'Timed out'), 'AUTH_REQUIRED': ('Giriş gerekiyor', 'Login required'),
                'AUTH_ERROR': ('Giriş doğrulanamadı', 'Authentication failed'),
                'ACCESS_RESTRICTED': ('Sağlayıcı erişimi kısıtlı', 'Provider access restricted'),
                'UNKNOWN_FAILURE': ('Nedeni doğrulanmamış hata', 'Unverified failure'),
            }
            parts.append(word('Süreç: ', 'Process: ') + classifications.get(
                item['classification'], ('Bilinmiyor', 'Unknown'))[index])
        task = item.get('task_result')
        if isinstance(task, dict):
            verdicts = {'BLOCKED': ('Engellendi', 'Blocked'), 'UNVERIFIED': ('Doğrulanmadı', 'Unverified'),
                        'FAIL': ('Başarısız', 'Failed'), 'FAILED': ('Başarısız', 'Failed'),
                        'REWORK_REQUIRED': ('Düzeltme gerekiyor', 'Rework required'),
                        'PASS': ('Geçti', 'Passed'), 'DONE': ('Tamamlandı', 'Completed'),
                        'SUCCESS': ('Başarılı', 'Successful'), 'COMPLETED': ('Tamamlandı', 'Completed')}
            for key in ('status', 'verdict'):
                if key in task:
                    value = task[key] if isinstance(task[key], str) else None
                    parts.append(word('Ajan beyanı: ', 'Agent report: ') + verdicts.get(
                        value, ('Bilinmiyor', 'Unknown'))[index])
            parts.append(word('Görev kabulü: ayrı doğrulama ve inceleme gerekiyor',
                              'Task acceptance: separate verification and review required'))
        return ' | '.join(parts)
    if 'event' in data:
        events = {'thread.started': ('Oturum başladı', 'Session started'), 'turn.started': ('Yanıt başladı', 'Turn started'),
                  'turn.completed': ('Yanıt tamamlandı', 'Turn completed'), 'turn.failed': ('Yanıt başarısız', 'Turn failed'),
                  'step_start': ('Adım başladı', 'Step started'), 'step_finish': ('Adım sona erdi', 'Step ended'),
                  'tool_use': ('Araç çalışması', 'Tool activity'), 'item.started': ('İş başladı', 'Item started'),
                  'item.completed': ('İş sona erdi', 'Item ended'), 'error': ('Hata', 'Error')}
        item = dict(data, tools=[{'tool': data['tool'], 'state': data.get('state')}] if data.get('tool') else [])
        return events.get(data['event'], ('Etkinlik', 'Activity'))[index] + ' | ' + row(item)
    if 'sessions' in data or 'runs' in data:
        rows = data.get('sessions', data.get('runs', []))
        heading = word('Ajan durumu', 'Agent status') if 'sessions' in data else word('Çalıştırmalar', 'Runs')
        if data.get('server') is not None:
            heading += ': ' + state(data['server'])
        return '\n'.join([heading, *(row(item) for item in rows if isinstance(item, dict))] +
                         ([] if rows else [word('Henüz ajan oturumu yok.', 'No agent sessions yet.')]))
    return row(data)


class ProcessTree:
    """Contain descendants before the first instruction of a Windows child."""
    def __init__(self, name=None, existing=False):
        self.name = name or 'store-' + uuid.uuid4().hex
        self.job = None
        self.proc = None
        if os.name != 'nt':
            return
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        signatures = {
            'CreateJobObjectW': ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            'OpenJobObjectW': ([w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'GetCurrentProcess': ([], w.HANDLE),
            'DuplicateHandle': ([w.HANDLE, w.HANDLE, w.HANDLE, ctypes.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD], w.BOOL),
            'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
            'Thread32First': ([w.HANDLE, ctypes.c_void_p], w.BOOL),
            'Thread32Next': ([w.HANDLE, ctypes.c_void_p], w.BOOL),
            'OpenThread': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'ResumeThread': ([w.HANDLE], w.DWORD),
            'IsProcessInJob': ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
        }
        for name_, (args, result) in signatures.items():
            function = getattr(k, name_)
            function.argtypes, function.restype = args, result
        self.job = k.OpenJobObjectW(12, False, self.name) if existing else k.CreateJobObjectW(None, self.name)
        if not self.job:
            raise OSError('Owned process-tree containment unavailable')
        if not existing:
            class Basic(ctypes.Structure):
                _fields_ = [('user', ctypes.c_longlong), ('job', ctypes.c_longlong), ('flags', w.DWORD),
                            ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t),
                            ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
            class Extended(ctypes.Structure):
                _fields_ = [('basic', Basic), ('io', ctypes.c_ulonglong * 6),
                            ('memory', ctypes.c_size_t * 4)]
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
            if not k.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                k.CloseHandle(self.job)
                self.job = None
                raise OSError('Cannot enforce process-tree containment')

    def spawn(self, argv, **kwargs):
        if os.name != 'nt':
            self.proc = subprocess.Popen(argv, start_new_session=True, **kwargs)
            return self.proc
        from ctypes import wintypes as w
        k = self.kernel
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | 4  # CREATE_SUSPENDED.
        self.proc = subprocess.Popen(argv, **kwargs)
        process = k.OpenProcess(0x1141, False, self.proc.pid)
        try:
            if not process or not k.AssignProcessToJobObject(self.job, process):
                raise OSError(ctypes.get_last_error(), 'Cannot assign suspended process to owned job')
            class ThreadEntry(ctypes.Structure):
                _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('thread', w.DWORD),
                            ('owner', w.DWORD), ('base', w.LONG), ('delta', w.LONG), ('flags', w.DWORD)]
            snapshot = k.CreateToolhelp32Snapshot(4, 0)
            if snapshot == ctypes.c_void_p(-1).value:
                raise OSError('Cannot inspect suspended process thread')
            threads = []
            try:
                entry = ThreadEntry()
                entry.size = ctypes.sizeof(entry)
                more = k.Thread32First(snapshot, ctypes.byref(entry))
                while more:
                    if entry.owner == self.proc.pid:
                        threads.append(entry.thread)
                    more = k.Thread32Next(snapshot, ctypes.byref(entry))
            finally:
                k.CloseHandle(snapshot)
            if len(threads) != 1:
                raise OSError('Unexpected suspended process threads; refusing execution')
            thread = k.OpenThread(2, False, threads[0])
            try:
                if not thread or k.ResumeThread(thread) != 1:
                    raise OSError('Cannot resume contained process')
            finally:
                if thread:
                    k.CloseHandle(thread)
            return self.proc
        except BaseException:
            self.proc.kill()
            self.proc.wait(timeout=5)
            self.close()
            for pipe in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if pipe:
                    pipe.close()
            raise
        finally:
            if process:
                k.CloseHandle(process)

    def close(self):
        try:
            self._close()
        except (OSError, RuntimeError) as error:
            raise ContainmentError('Owned process-tree termination is unverified; preserve dispatch lock') from error

    def _close(self):
        if os.name == 'nt' and self.job:
            from ctypes import wintypes as w
            k = self.kernel
            if not k.TerminateJobObject(self.job, 1):
                raise OSError('Cannot terminate owned process tree; reconciliation required')
            class Accounting(ctypes.Structure):
                _fields_ = [('times', ctypes.c_longlong * 4), ('faults', w.DWORD),
                            ('total', w.DWORD), ('active', w.DWORD), ('terminated', w.DWORD)]
            accounting = Accounting()
            for _ in range(50):
                if not k.QueryInformationJobObject(self.job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                    raise OSError('Cannot verify owned process-tree termination')
                if accounting.active == 0:
                    k.CloseHandle(self.job)
                    self.job = None
                    return
                time.sleep(.1)
            raise RuntimeError('Owned descendants remain; reconciliation required')
        elif os.name != 'nt' and self.proc:
            import signal
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc = None

    def detach_server(self):
        """A non-inheritable server-held job handle keeps persistent ownership."""
        if os.name == 'nt':
            from ctypes import wintypes as w
            target = self.kernel.OpenProcess(0x40, False, self.proc.pid)
            duplicate = w.HANDLE()
            try:
                if not target or not self.kernel.DuplicateHandle(self.kernel.GetCurrentProcess(), self.job,
                        target, ctypes.byref(duplicate), 0, False, 2):
                    raise OSError('Cannot persist server process-tree ownership')
            finally:
                if target:
                    self.kernel.CloseHandle(target)
            self.kernel.CloseHandle(self.job)
            self.job = None


def state_path(project):
    project = Path(project).resolve(strict=True)
    path = project / '.factory/runs/native-server.json'
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (path, *path.parents) if p != project and project in p.parents):
        raise ValueError('Linked session state refused')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def process_identity(pid, terminate_expected=None):
    """Creation stamp plus image; PID reuse cannot stop a different process."""
    if os.name == 'nt':
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        handle = kernel.OpenProcess(0x1000 | (0x100001 if terminate_expected else 0), False, pid)
        if not handle:
            return None
        try:
            stamps = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(s) for s in stamps)):
                return None
            size = wintypes.DWORD(32768)
            image = ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                return None
            birth = (stamps[0].dwHighDateTime << 32) | stamps[0].dwLowDateTime
            identity = {'birth': str(birth), 'image': str(Path(image.value).resolve())}
            if terminate_expected is not None:
                if identity != terminate_expected:
                    raise RuntimeError('Owned PID identity changed; refusing stop')
                if not kernel.TerminateProcess(handle, 0):
                    raise OSError('Cannot terminate owned native server')
                if kernel.WaitForSingleObject(handle, 5000) != 0:
                    raise RuntimeError('Owned server did not stop within five seconds')
            return identity
        finally:
            kernel.CloseHandle(handle)
    try:
        # /proc stat's command may contain spaces and parentheses.
        birth = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        return {'birth': birth, 'image': str(Path(f'/proc/{pid}/exe').resolve(strict=True))}
    except (OSError, IndexError):
        return None


def load_state(project, require_live=True):
    project = Path(project).resolve(strict=True)
    data = json.loads(state_path(project).read_text(encoding='utf-8'))
    if data.get('project') != str(project) or not isinstance(data.get('pid'), int):
        raise ValueError('Session server belongs to another project')
    if not re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{0,4}', data.get('url', '')):
        raise ValueError('Only owned loopback endpoints allowed')
    identity = process_identity(data['pid'])
    if require_live and (not identity or identity != data.get('identity')):
        raise RuntimeError('Owned server is stopped or PID was reused; start a fresh server')
    if data.get('identity') and Path(data.get('binary', '')).resolve() != Path(data['identity']['image']).resolve():
        raise ValueError('Session binary differs from owned process image')
    return data


def store(project, data):
    path = state_path(project)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='native-state-', suffix='.tmp', delete=False) as stream:
        json.dump(data, stream, indent=2)
        temp = Path(stream.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def config_digest(env):
    config = env.get('OPENCODE_CONFIG_CONTENT')
    if not config:
        raise ValueError('Validated native permission configuration required')
    return hashlib.sha256(config.encode()).hexdigest()


def validate_config(state, env):
    if state.get('config_sha256') != config_digest(env):
        raise ValueError('Server permissions differ; start an exact task-scoped server')


def api(project, state, env, endpoint, method='GET', body=None):
    if method not in ('GET', 'POST') or not re.fullmatch(r'/[A-Za-z0-9_/-]+', endpoint):
        raise ValueError('Unsupported native API request')
    if method == 'POST':
        current = load_state(project)
        validate_config(current, env)
        if any(current.get(key) != state.get(key) for key in ('url', 'pid', 'identity')):
            raise ValueError('Native server changed before intervention')
    password = env.get('OPENCODE_SERVER_PASSWORD')
    if not password:
        raise ValueError('Local server password required in native environment')
    auth = base64.b64encode(('opencode:' + password).encode()).decode()
    url = state['url'] + endpoint + '?' + urlencode({'directory': str(Path(project).resolve())})
    payload = json.dumps(body).encode('utf-8') if body is not None else None
    request = Request(url, data=payload, method=method,
                      headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    with build_opener(NoRedirect).open(request, timeout=3) as response:
        payload = response.read()
        return json.loads(payload) if payload else None


def owned_session(project, env, session_id):
    state = load_state(project)
    validate_config(state, env)
    if not isinstance(session_id, str) or not re.fullmatch(r'ses_[A-Za-z0-9]+', session_id):
        raise ValueError('Invalid native session ID')
    rows = project_sessions(project, api(project, state, env, '/session'))
    if session_id not in {row['id'] for row in rows}:
        raise ValueError('Session is not owned by the selected project')
    return state


def intervene(project, env, session_id, prompt=None, abort=False):
    state = owned_session(project, env, session_id)
    if abort:
        if api(project, state, env, '/session/' + session_id + '/abort', method='POST') is not True:
            raise RuntimeError('Native abort was not acknowledged')
        return {'event': 'intervention', 'session': session_id, 'state': 'interrupted'}
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 16000:
        raise ValueError('Intervention requires 1..16000 characters')
    api(project, state, env, '/session/' + session_id + '/prompt_async', method='POST',
        body={'parts': [{'type': 'text', 'text': prompt}]})
    return {'event': 'intervention', 'session': session_id, 'state': 'pending'}


def report_contract(project, env, path):
    project = Path(project).resolve(strict=True)
    path = Path(path).absolute()
    if project not in path.parents or any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                                        for p in (path, *path.parents) if p != project):
        raise ValueError('Report contract must be an unlinked project file')
    path = path.resolve(strict=True)
    if project not in path.parents:
        raise ValueError('Report contract escaped the project')
    raw = path.read_bytes()
    if len(raw) > 64000:
        raise ValueError('Report contract exceeds the native record limit')
    state = load_state(project)
    validate_config(state, env)
    if hashlib.sha256(raw).hexdigest() != state.get('contract_sha256'):
        raise ValueError('Report contract differs from validated dispatch')
    contract = json.loads(raw)
    if contract.get('task_id') != state.get('task_id'):
        raise ValueError('Report contract task differs from dispatch')
    return contract


def relay_updates(project, env, contract=None):
    """Observe native messages; notify parents without launching an inference turn."""
    state = load_state(project)
    validate_config(state, env)
    rows = project_sessions(project, api(project, state, env, '/session'))
    rows = [row for row in rows if row.get('time', {}).get('created', 0) >= state['started_at'] * 1000
            or row['id'] in state.get('resume_sessions', [])]
    ids = {row['id'] for row in rows}
    observed = state.get('relay_observed', {})
    delivered = set(state.get('relay_delivered', []))
    notice_ids = {'msg_' + hashlib.sha256(key.encode()).hexdigest()[:24] for key in delivered}
    reports = state.get('agent_reports', {})
    events = []
    for row in rows:
        sid, parent = row['id'], row.get('parentID')
        messages = api(project, state, env, '/session/' + sid + '/message')
        user_order = [m.get('info', {}).get('id') for m in messages if m.get('info', {}).get('role') == 'user']
        user_order = [mid for mid in user_order if isinstance(mid, str) and re.fullmatch(r'msg_[A-Za-z0-9]+', mid) and mid not in notice_ids]
        user_ids = set(user_order)
        # Only the first native user message is the delegated prompt, even before first poll.
        previous = set(observed.get(sid, user_order[:1]))
        notices = [('intervention', mid) for mid in sorted(user_ids - previous)]
        if contract is not None:
            if not isinstance(contract.get('task_id'), str) or contract.get('task_id') != state.get('task_id'):
                raise ValueError('Report task differs from dispatch')
            try:
                from .subscriptions import REPORT_FIELDS, report_valid
            except ImportError:
                from subscriptions import REPORT_FIELDS, report_valid
            for message in messages:
                info = message.get('info', {})
                mid = info.get('id')
                if info.get('role') != 'assistant' or not info.get('time', {}).get('completed') or not isinstance(mid, str) or not re.fullmatch(r'msg_[A-Za-z0-9]+', mid):
                    continue
                text_parts = [part.get('text', '') for part in message.get('parts', [])
                              if part.get('type') == 'text' and isinstance(part.get('text'), str)]
                text_body = '\n'.join(text_parts)
                if len(text_body) > 64000:
                    continue
                try:
                    report = json.loads(text_body)
                except (ValueError, TypeError):
                    continue
                if report_valid(report, contract['task_id']):
                    key = sid + ':' + mid
                    if key not in reports:
                        reports[key] = {field: report[field] for field in REPORT_FIELDS}
                        notices.append(('report', mid))
        for kind, mid in notices:
            key = sid + ':' + kind + ':' + mid
            if parent not in ids or key in delivered:
                continue
            notice = {'event': kind, 'child_session': sid, 'message': mid,
                      'task_id': state.get('task_id'), 'source': 'native_session_messages'}
            # Deterministic message ID makes a crash after POST safe to retry without a new turn.
            notice_id = 'msg_' + hashlib.sha256(key.encode()).hexdigest()[:24]
            receipt = api(project, owned_session(project, env, parent), env, '/session/' + parent + '/message', method='POST',
                body={'messageID': notice_id, 'noReply': True,
                      'parts': [{'type': 'text', 'text': json.dumps(notice, separators=(',', ':'))}]})
            if not isinstance(receipt, dict) or receipt.get('info', {}).get('role') != 'user' or receipt['info'].get('id') != notice_id:
                raise RuntimeError('Native noReply notification was not acknowledged')
            delivered.add(key)
            notice_ids.add('msg_' + hashlib.sha256(key.encode()).hexdigest()[:24])
            events.append({'event': kind, 'session': parent, 'child_session': sid, 'state': 'completed'})
        observed[sid] = sorted(user_ids)
    current = load_state(project)
    current.update(relay_observed=observed, relay_delivered=sorted(delivered), agent_reports=reports)
    store(project, current)
    return events


def start(project, binary, env, language='tr'):
    project = Path(project).resolve(strict=True)
    language = display_language(language)
    if not env.get('OPENCODE_SERVER_PASSWORD'):
        raise ValueError('Supply a private local server password before starting')
    fingerprint = config_digest(env)
    path = state_path(project)
    lock = path.with_suffix('.lock')
    # ponytail: one server per project; a supervisor manages cross-project capacity.
    lock.open('x').close()
    try:
        if path.exists():
            old = load_state(project, require_live=False)
            if old.get('identity') and process_identity(old['pid']) == old['identity']:
                raise RuntimeError('Project already has an owned live server')
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        native = dict(env, OPENCODE_SERVER_USERNAME='opencode')
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        tree = ProcessTree()
        proc = tree.spawn([str(binary), '--pure', 'serve', '--hostname', '127.0.0.1', '--port', str(port)],
                          cwd=project, env=native, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        identity = process_identity(proc.pid)
        data = {'project': str(project), 'pid': proc.pid, 'identity': identity,
                'url': f'http://127.0.0.1:{port}', 'binary': str(Path(binary).resolve()),
                'state': 'STARTING', 'language': language, 'started_at': time.time(), 'config_sha256': fingerprint,
                'job': tree.name, 'terminal_window': 'store-' + uuid.uuid4().hex}
        try:
            store(project, data)
            if not identity:
                raise RuntimeError('Cannot establish native process ownership')
            for _ in range(40):
                if proc.poll() is not None:
                    raise RuntimeError('Native server exited before readiness')
                try:
                    current = api(project, data, native, '/path')
                    if Path(current['directory']).resolve() != project:
                        raise RuntimeError('Native server project mismatch')
                    data['state'] = 'RUNNING'
                    store(project, data)
                    tree.detach_server()
                    return data
                except (OSError, ValueError, KeyError):
                    time.sleep(.25)
            raise RuntimeError('Native server readiness timed out')
        except BaseException:
            tree.close()
            proc.wait(timeout=5)
            data['state'] = 'FAILED'
            store(project, data)
            raise
    finally:
        lock.unlink(missing_ok=True)


def project_sessions(project, rows):
    project = Path(project).resolve(strict=True)
    return [row for row in rows if isinstance(row, dict)
            and isinstance(row.get('id'), str) and re.fullmatch(r'ses_[A-Za-z0-9]+', row['id'])
            and isinstance(row.get('directory'), str)
            and Path(row['directory']).resolve() == project]


def normalize_usage(info):
    """Reported OpenCode message counters; absent fields are unknown, never zero."""
    info = info if isinstance(info, dict) else {}
    tokens = info.get('tokens') if isinstance(info.get('tokens'), dict) else {}
    cache = tokens.get('cache') if isinstance(tokens.get('cache'), dict) else {}
    def count(value):
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None
    return {key: count(value) for key, value in {
        'input': tokens.get('input'), 'output': tokens.get('output'),
        'reasoning': tokens.get('reasoning'), 'cache_read': cache.get('read'),
        'cache_write': cache.get('write'), 'reported_cost': info.get('cost')}.items()}


def public_event(event):
    """Only structural activity; never source, tool output or hidden reasoning."""
    if not isinstance(event, dict):
        return None
    kind = event.get('type')
    part = event.get('part') or event.get('item') or {}
    part = part if isinstance(part, dict) else {}
    state = part.get('state') if isinstance(part.get('state'), dict) else {}
    metadata = state.get('metadata') if isinstance(state.get('metadata'), dict) else {}
    result = {'event': kind} if kind in {
        'thread.started', 'turn.started', 'turn.completed', 'turn.failed', 'error',
        'step_start', 'step_finish', 'tool_use', 'item.started', 'item.completed'} else None
    if result is None:
        return None
    for key, value in {'session': event.get('sessionID') or event.get('thread_id'),
                       'tool': part.get('tool'), 'state': state.get('status')}.items():
        if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', value):
            result[key] = value
    child = metadata.get('sessionId')
    if isinstance(child, str) and re.fullmatch(r'ses_[A-Za-z0-9]+', child):
        result['child_session'] = child
    if kind == 'step_finish':
        result['usage'] = normalize_usage(part)
    elif kind == 'turn.completed':
        reported = event.get('usage') if isinstance(event.get('usage'), dict) else {}
        result['usage'] = normalize_usage({'tokens': {
            'input': reported.get('input_tokens'), 'output': reported.get('output_tokens'),
            'cache': {'read': reported.get('cached_input_tokens')}}})
    return result


def reported_usage(stdout):
    counters = []
    for line in stdout.splitlines():
        try:
            event = public_event(json.loads(line))
            if event and 'usage' in event:
                counters.append(event['usage'])
        except (ValueError, TypeError, AttributeError):
            continue
    return {key: sum(c[key] for c in counters) if counters and all(c[key] is not None for c in counters) else None
            for key in normalize_usage({})}


def stream_run(argv, project, env, timeout=300, input_text=None, emit=None, metadata=None):
    """Drop-in model subprocess result plus durable sanitized lifecycle evidence.

    Full output is returned in memory for existing verdict parsing; activity files
    contain no message bodies. Caller still owns dispatch lock/contract validation.
    """
    language = display_language((metadata or {}).get('language', 'tr'))
    root = state_path(project).parent
    stem = root / ('live-' + uuid.uuid4().hex)
    lifecycle = stem.with_suffix('.json')
    events = stem.with_suffix('.jsonl')
    started = time.monotonic()
    data = {'project': str(Path(project).resolve()), 'state': 'STARTING', 'pid': None, 'language': language,
            'started_at': time.time(), 'events': events.name, 'usage': normalize_usage({})}
    data['native_sessions'] = []
    for key in ('provider', 'model', 'effort', 'task_id', 'role', 'contract_sha256'):
        value = (metadata or {}).get(key)
        if isinstance(value, str) and re.fullmatch(r'[\w ./:-]{1,160}', value):
            data[key] = value
    def checkpoint():
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root,
                                         prefix='live-state-', suffix='.tmp', delete=False) as stream:
            json.dump(data, stream, indent=2)
            temp = Path(stream.name)
        try:
            temp.replace(lifecycle)
        finally:
            temp.unlink(missing_ok=True)
    checkpoint()
    proc = None
    tree = None
    output = {'stdout': [], 'stderr': []}
    usage_events = 0
    lines = queue.Queue()
    finished = set()
    def read(name, pipe):
        try:
            for line in pipe:
                lines.put((name, line))
        finally:
            pipe.close()
            lines.put((name, None))
    try:
        tree = ProcessTree()
        proc = tree.spawn(argv, cwd=project, env=env, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace')
        data.update(state='RUNNING', pid=proc.pid)
        checkpoint()
        for name in output:
            threading.Thread(target=read, args=(name, getattr(proc, name)), daemon=True).start()
        if input_text is not None:
            def write_input():
                try:
                    proc.stdin.write(input_text)
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass
            threading.Thread(target=write_input, daemon=True).start()
        timed_out = False
        with events.open('x', encoding='utf-8') as log:
            while len(finished) < 2:
                if time.monotonic() - started >= timeout:
                    timed_out = True
                    tree.close()
                    break
                try:
                    name, line = lines.get(timeout=.1)
                except queue.Empty:
                    continue
                if line is None:
                    finished.add(name)
                    continue
                output[name].append(line)
                try:
                    event = public_event(json.loads(line)) if name == 'stdout' else None
                except (ValueError, TypeError, AttributeError):
                    event = None
                if event:
                    log.write(json.dumps(event, ensure_ascii=True) + '\n')
                    log.flush()
                    data['latest'] = event
                    for key in ('session', 'child_session'):
                        native_id = event.get(key)
                        if native_id and native_id not in data['native_sessions']:
                            data['native_sessions'].append(native_id)
                    if 'usage' in event:
                        data['usage'] = {key: value if usage_events == 0 else
                                         (data['usage'][key] + value if data['usage'][key] is not None and value is not None else None)
                                         for key, value in event['usage'].items()}
                        usage_events += 1
                    checkpoint()
                    if emit:
                        emit(event)
            code = 124 if timed_out else proc.wait(timeout=max(1, timeout - (time.monotonic() - started)))
        if timed_out:
            proc.wait(timeout=5)
        tree.close()  # Successful transport must not leave a background mutator.
        stdout, stderr = ''.join(output['stdout']), ''.join(output['stderr'])
        data.update(state='TIMEOUT' if timed_out else ('FINISHED' if code == 0 else 'FAILED'),
                    exit_code=code, finished_at=time.time(), usage=reported_usage(stdout))
        checkpoint()
        return {'command': argv, 'exit_code': code, 'stdout': stdout,
                'stderr': stderr + ('\nTIMEOUT; inspect checkpoint before retry' if timed_out else ''),
                'duration_seconds': round(time.monotonic() - started, 2),
                'lifecycle': str(lifecycle), 'reported_usage': data['usage'],
                **{key: data[key] for key in ('provider', 'model', 'task_id', 'role', 'language') if key in data}}
    except BaseException:
        if tree is not None:
            tree.close()
        if proc is not None:
            proc.wait(timeout=5)
        data.update(state='INTERRUPTED' if isinstance(sys.exc_info()[1], KeyboardInterrupt) else 'FAILED',
                    finished_at=time.time())
        checkpoint()
        raise


def summarize(messages):
    assistants = [m for m in messages if m.get('info', {}).get('role') == 'assistant']
    usage = [normalize_usage(m['info']) for m in assistants]
    totals = {key: sum(u[key] for u in usage) if usage and all(u[key] is not None for u in usage) else None
              for key in normalize_usage({})}
    latest = assistants[-1] if assistants else {}
    info = latest.get('info', {})
    tools = [{'tool': p.get('tool'), 'state': p.get('state', {}).get('status')}
             for p in latest.get('parts', []) if p.get('type') == 'tool'
             and re.fullmatch(r'[\w.-]{1,64}', p.get('tool', ''))]
    # Never display prompts, tool inputs/output, reasoning, paths or arbitrary titles.
    return {'agent': info.get('agent'), 'provider': info.get('providerID'), 'model': info.get('modelID'),
            'tools': tools, 'usage': totals, 'quota_remaining': None,
            'usage_source': 'native_assistant_messages', 'messages': len(assistants)}


def status(project, env):
    data = load_state(project)
    rows = project_sessions(project, api(project, data, env, '/session'))
    rows = [row for row in rows if row.get('time', {}).get('created', 0) >= data['started_at'] * 1000
            or row['id'] in data.get('resume_sessions', [])]
    states = api(project, data, env, '/session/status')
    sessions = []
    for row in rows:
        info = summarize(api(project, data, env, '/session/' + row['id'] + '/message'))
        parent = row.get('parentID')
        sessions.append({'id': row['id'], 'parent': parent if parent in {r['id'] for r in rows} else None,
                         'state': states.get(row['id'], {}).get('type', 'idle'), **info})
    return {'project': data['project'], 'server': data['state'], 'sessions': sessions,
            'language': display_language(data.get('language', 'tr'))}


def attach_command(project, env, session_id=None):
    state = load_state(project)
    validate_config(state, env)
    if session_id:
        rows = project_sessions(project, api(project, state, env, '/session'))
        if session_id not in {r['id'] for r in rows}:
            raise ValueError('Session is not owned by the selected project')
    argv = [state['binary'], '--pure', 'attach', state['url'], '--dir', str(Path(project).resolve())]
    if session_id:
        argv += ['--session', session_id]
    return argv


def pane_layout(index):
    """Keep activity above the director, then balance only the worker region."""
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ValueError('Pane index must be a nonnegative integer')
    if index < 2:
        return (index, '-H', '.8') if index == 0 else (1, '-V', '.6')
    # ponytail: recompute the small team tree; large teams should retain this layout state.
    workers = [(1, 0)]
    for created in range(2, index + 1):
        target = max(range(len(workers)), key=lambda position: workers[position][0])
        area, depth = workers[target]
        if created == index:
            return target + 2, '-H' if depth % 2 == 0 else '-V', '.5'
        # Native nextInOrder traverses tree leaves, so a split inserts beside its target.
        workers[target:target + 1] = [(area / 2, depth + 1)] * 2


def terminal_command(project, argv, split=False, role='factory', language='tr', pane_index=None):
    if any(';' in str(arg) for arg in argv):
        raise ValueError('Windows Terminal command separator in an argument refused')
    terminal = shutil.which('wt.exe')
    if not terminal:
        raise RuntimeError('Windows Terminal unavailable; use native attach in this terminal')
    name = load_state(project)['terminal_window']
    if not isinstance(name, str) or not re.fullmatch(r'store-[a-f0-9]{32}', name):
        raise ValueError('Invalid owned terminal window')
    # argv stays an argv vector, with no PowerShell/cmd string evaluation.
    command = [terminal, '-w', name]
    layout = []
    if split and pane_index is not None:
        # Owned tab must remain open and in place; native user rearrangement needs a new view.
        target, direction, size = pane_layout(pane_index)
        command += ['focus-tab', '--target', '0', ';', 'move-focus', 'first', ';']
        for _ in range(target):
            command += ['move-focus', 'nextInOrder', ';']
        layout = [direction, '--size', size]
    return [*command, 'split-pane' if split else 'new-tab', *layout,
            '--title', role_name(role, language), '--suppressApplicationTitle',
            '--colorScheme', 'One Half Dark', *argv]


def attach(project, env, session_id=None, pane=False, role=None, language=None, pane_index=None):
    argv = attach_command(project, env, session_id)
    if pane:
        language = display_language(language or load_state(project).get('language', 'tr'))
        if role is None and session_id:
            role = next((row.get('agent') for row in status(project, env)['sessions']
                         if row['id'] == session_id), None)
        command = terminal_command(project, argv, split=True, role=role, language=language, pane_index=pane_index)
        subprocess.run(command, env=env, check=True)
        return {'state': 'NATIVE_TERMINAL_OPENED', 'session': session_id}
    return {'exit_code': subprocess.call(argv, cwd=project, env=env)}


def stop(project):
    state = load_state(project)
    # Recheck immediately before signaling; never stop by port or executable name.
    if process_identity(state['pid']) != state['identity']:
        raise RuntimeError('Owned PID identity changed; refusing stop')
    if os.name == 'nt':
        from ctypes import wintypes as w
        if not re.fullmatch(r'store-[a-f0-9]{32}', state.get('job', '')):
            raise ValueError('Owned process-tree identity missing')
        tree = ProcessTree(state['job'], existing=True)
        process = tree.kernel.OpenProcess(0x1000, False, state['pid'])
        member = w.BOOL()
        try:
            if not process or not tree.kernel.IsProcessInJob(process, tree.job, ctypes.byref(member)) or not member.value:
                tree.kernel.CloseHandle(tree.job)
                tree.job = None
                raise RuntimeError('Process does not belong to owned server job')
            tree.close()
        finally:
            if process:
                tree.kernel.CloseHandle(process)
    else:
        import signal
        os.killpg(state['pid'], signal.SIGKILL)
    state['state'] = 'STOPPED'
    state['stopped_at'] = time.time()
    store(project, state)
    return {'state': 'STOPPED', 'pid': state['pid'], 'language': display_language(state.get('language', 'tr'))}


def watch(project, env, interval=2, emit=print, auto_panes=False, language=None, json_output=False, relay=False, contract=None):
    if language is not None:
        display_language(language)
    previous = None
    attached = set()
    try:
        while True:
            current = status(project, env)
            language = language or current.get('language', 'tr')
            if relay:
                for event in relay_updates(project, env, contract):
                    emit(json.dumps(event) if json_output else format_public(event, language))
            if auto_panes:
                # Parents precede specialists so the director retains the first agent pane.
                for session in sorted(current['sessions'], key=lambda item: bool(item.get('parent'))):
                    if session['id'] not in attached:
                        attach(project, env, session['id'], pane=True,
                               role=session.get('agent') or ('factory' if not session.get('parent') else None),
                               language=language or current.get('language', 'tr'),
                               pane_index=len(attached))
                        attached.add(session['id'])
            rendered = json.dumps(current, ensure_ascii=True, sort_keys=True)
            if rendered != previous:
                emit(rendered if json_output else format_public(current, language))
                previous = rendered
            time.sleep(max(1, interval))
    except KeyboardInterrupt:
        return {'state': 'WATCH_CLOSED', 'server': 'unchanged', 'language': language or 'tr'}
    except (OSError, RuntimeError) as error:
        state = load_state(project, require_live=False)
        language = language or state.get('language', 'tr')
        if state.get('state') in ('STOPPED', 'FAILED') or process_identity(state['pid']) != state.get('identity'):
            final = {'state': 'WATCH_CLOSED', 'server': state['state'] if state.get('state') in ('STOPPED', 'FAILED') else 'STOPPED',
                     'language': language}
            emit(json.dumps(final) if json_output else format_public(final, language))
            return final
        raise error


def handle(action, project, binary, env, session_id=None, pane=False, language=None, json_output=False):
    if language is not None:
        display_language(language)
    if action == 'start':
        data = start(project, binary, env, language or 'tr')
        if pane:
            argv = attach_command(project, env)
            command = terminal_command(project, argv, language=data['language'])
            watch_argv = [sys.executable, str(Path(__file__).resolve()), 'watch', '--project', str(Path(project).resolve()),
                          '--language', data['language']]
            if any(';' in arg for arg in watch_argv):
                raise ValueError('Windows Terminal separator refused')
            command += [';', 'split-pane', '--title', role_name('activity', data['language']), *watch_argv]
            subprocess.run(command, env=env, check=True)
        return data
    if action == 'status':
        return status(project, env)
    if action == 'watch':
        return watch(project, env, language=language, json_output=json_output)
    if action == 'attach':
        return attach(project, env, session_id, pane, language=language)
    if action == 'stop':
        return stop(project)
    raise ValueError('Unknown native session action')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'watch', 'attach', 'stop'])
    parser.add_argument('--project', default=os.getcwd())
    parser.add_argument('--binary', default=shutil.which('opencode.exe'))
    parser.add_argument('--session')
    parser.add_argument('--pane', action='store_true')
    parser.add_argument('--language', choices=['tr', 'en'])
    parser.add_argument('--json', action='store_true', help='Machine-readable structural output')
    parser.add_argument('--auto-panes', action='store_true', help='Watch and open every observed native agent session in balanced panes')
    parser.add_argument('--relay', action='store_true', help='Relay structural intervention/report notices without inference')
    parser.add_argument('--contract', help='Exact validated dispatch contract for native report collection')
    args = parser.parse_args()
    if args.action == 'watch':
        env = dict(os.environ)
        contract = report_contract(args.project, env, args.contract) if args.contract else None
        result = watch(args.project, env, auto_panes=args.auto_panes, language=args.language, json_output=args.json,
                       relay=args.relay, contract=contract)
    elif args.auto_panes or args.relay or args.contract:
        parser.error('--auto-panes, --relay and --contract require watch')
    else:
        result = handle(args.action, args.project, args.binary, dict(os.environ), args.session, args.pane,
                        language=args.language, json_output=args.json)
    print(json.dumps(result) if args.json else format_public(result, args.language))
