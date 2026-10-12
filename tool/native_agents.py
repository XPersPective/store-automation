"""Native, owned app-server/ACP sessions; bounded source snapshots, no source writes."""
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from collections import deque
from pathlib import Path, PureWindowsPath

try:
    from .sessions import ProcessTree, ContainmentError
    from .factory import clean_ai_env, sensitive_path
except ImportError:
    from sessions import ProcessTree, ContainmentError
    from factory import clean_ai_env, sensitive_path

MAX_LINE = 256_000
MAX_EVENTS = 128
MAX_TEXT = 64_000
MAX_TURN_SECONDS = 300


class Rpc:
    """Bounded newline JSON-RPC over one ProcessTree-contained native child."""
    def __init__(self, tree, argv, cwd, env, timeout=30, on_notification=None, before_spawn_resume=None):
        self.tree, self.timeout = tree, timeout
        self.on_notification = on_notification
        self.pending = {}
        self.pending_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.events = deque(maxlen=MAX_EVENTS)
        self.event_queue = queue.Queue(MAX_EVENTS)
        self.proc = tree.spawn(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding='utf-8', bufsize=1, before_resume=before_spawn_resume)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.identity = 0

    def _read(self):
        try:
            for line in iter(lambda: self.proc.stdout.readline(MAX_LINE + 1), ''):
                if len(line) > MAX_LINE:
                    break
                try:
                    message = json.loads(line)
                except ValueError:
                    break
                if not isinstance(message, dict):
                    continue
                identity = message.get('id')
                with self.pending_lock:
                    target = self.pending.get(identity) if identity is not None else None
                if target:
                    try:
                        target.put(message, timeout=.1)
                    except queue.Full:
                        continue
                elif 'method' in message and identity is not None:
                    self.deny(message)
                elif 'method' in message:
                    self.events.append(message)
                    if self.on_notification:
                        try:
                            self.on_notification(message)
                        except Exception:
                            pass
                    if self.event_queue.full():
                        try:
                            self.event_queue.get_nowait()
                        except queue.Empty:
                            pass
                    try:
                        self.event_queue.put_nowait(message)
                    except queue.Full:
                        pass
        finally:
            with self.pending_lock:
                pending = list(self.pending.values())
            for target in pending:
                try:
                    target.put_nowait(None)
                except queue.Full:
                    pass

    def request(self, method, params):
        target = queue.Queue(1)
        with self.pending_lock:
            self.identity += 1
            identity = self.identity
            self.pending[identity] = target
        try:
            self._write({'id': identity, 'method': method, 'params': params})
            left = self.timeout
            if left <= 0:
                raise TimeoutError('native RPC deadline reached')
            message = target.get(timeout=left)
            if message is None:
                raise RuntimeError('native RPC stream ended')
            if 'error' in message or not isinstance(message.get('result'), dict):
                raise RuntimeError('native RPC request failed')
            return message['result']
        finally:
            with self.pending_lock:
                self.pending.pop(identity, None)

    def _write(self, message):
        with self.write_lock:
            self.proc.stdin.write(json.dumps(message) + '\n')
            self.proc.stdin.flush()

    def deny(self, request):
        if 'id' in request:
            self._write({'id': request['id'], 'error': {
                'code': -32000, 'message': 'Worker tool/approval request denied by source-only supervisor'}})

    def notify(self, method, params=None):
        self._write({'method': method, 'params': params or {}})

    def next_event(self, timeout=None):
        return self.event_queue.get(timeout=timeout)


def _source_snapshot(project, files, limit=200_000, ranges=None):
    root = Path(project).resolve(strict=True)
    if not isinstance(files, list) or not files or len(files) > 40:
        raise ValueError('Supply 1–40 source files')
    chunks, total = [], 0
    for name in files:
        relative = Path(name)
        if relative.is_absolute() or PureWindowsPath(name).anchor or '..' in PureWindowsPath(name).parts or sensitive_path(name):
            raise ValueError('Snapshot path must be project-relative')
        candidate = root / relative
        cursor = root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink() or (hasattr(cursor, 'is_junction') and cursor.is_junction()):
                raise ValueError('Snapshot path contains a link')
        path = candidate.resolve(strict=True)
        if root not in path.parents or not path.is_file() or sensitive_path(path) or path.stat().st_size > limit:
            raise ValueError('Snapshot path escapes project or is not a regular file')
        body = path.read_text(encoding='utf-8')
        if ranges and name in ranges:
            selected = ranges[name]
            if not isinstance(selected, list) or len(selected) != 2 or any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in selected) or selected[1] < selected[0]:
                raise ValueError('Invalid bounded source line range')
            lines = body.splitlines(keepends=True)
            if selected[1] > len(lines): raise ValueError('Source line range exceeds file')
            body = ''.join(lines[selected[0] - 1:selected[1]])
        total += len(body)
        if total > limit:
            raise ValueError('Source snapshot exceeds bounded context')
        chunks.append(f'--- {path.relative_to(root).as_posix()} ---\n{body}')
    return root, '\n'.join(chunks)


class CodexSession:
    """Interactive app-server protocol with source-only prompt and read-only sandbox."""
    def __init__(self, executable, project, model, effort, env, tree=None,
                 on_notification=None, before_resume=None):
        self.project = str(Path(project).resolve(strict=True))
        self.tree = tree or ProcessTree()
        self.rpc = None
        try:
            self.rpc = Rpc(self.tree, [executable, 'app-server', '--stdio', '-c', 'model_provider="openai"', '-c',
                                       'forced_login_method="chatgpt"'], self.project,
                           clean_ai_env(env), 30, on_notification, before_resume)
            self.rpc.request('initialize', {'clientInfo': {'name': 'store-automation-native', 'version': 'proposal'},
                                             'capabilities': {'experimentalApi': True}})
            self.rpc.notify('initialized')
            self.thread = self.rpc.request('thread/start', {'cwd': self.project, 'model': model,
                'sandbox': 'read-only', 'approvalPolicy': 'never', 'ephemeral': True,
                'baseInstructions': 'Source-only analysis. No shell, tools, edits, external resources, or delegation. '
                                    'Use only supplied snapshot and return a patch proposal as text.'})['thread']['id']
        except BaseException:
            self.tree.close()
            raise
        self.model, self.effort = model, effort
        self.turn = None
        self.before_resume = before_resume
        self.last_status = 'idle'
        self._operation_lock = threading.RLock()
        self._collector_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False

    def start(self, task, files, context_budget=MAX_TEXT, context_ranges=None):
        with self._operation_lock:
            if self.last_status != 'idle' or self._collector_lock.locked():
                raise RuntimeError('Native session already has an active or completed turn')
            return self._start(task, files, context_budget, context_ranges)

    def _start(self, task, files, context_budget, context_ranges=None):
        root, snapshot = _source_snapshot(self.project, files, ranges=context_ranges)
        if root != Path(self.project):
            raise ValueError('Project root changed')
        prompt = ('Analyze this bounded source snapshot; do not apply edits. Return the required typed JSON task report, '
                  'put any proposed diff in evidence as text, and follow the supervisor task contract. '
                  'No shell, tools, tests, credentials, or files outside the snapshot.\nTASK:\n' + task +
                  '\nSNAPSHOT:\n' + snapshot)
        if len(prompt) > min(MAX_TEXT, context_budget):
            raise ValueError('Turn input exceeds bounded message size')
        result = self.rpc.request('turn/start', {'threadId': self.thread,
            'input': [{'type': 'text', 'text': prompt, 'text_elements': []}],
            'model': self.model, 'effort': self.effort,
            'sandboxPolicy': {'type': 'readOnly'}})
        self.turn = result['turn']['id']
        self.last_status = 'running'
        return {'thread_id': self.thread, 'turn_id': self.turn}

    def collect(self, seconds=MAX_TURN_SECONDS):
        if not self._collector_lock.acquire(blocking=False):
            raise RuntimeError('A collector already owns the native turn stream')
        turn_id = self.turn
        deadline = time.monotonic() + min(max(seconds, 1), MAX_TURN_SECONDS)
        text = []
        text_size = 0
        status = 'timed_out'
        try:
            if not turn_id:
                raise RuntimeError('No native turn is active')
            while time.monotonic() < deadline:
                try:
                    message = self.rpc.next_event(timeout=max(.01, deadline - time.monotonic()))
                except queue.Empty:
                    break
                params = message.get('params', {})
                if params.get('threadId') != self.thread:
                    continue
                if (message.get('method') == 'item/agentMessage/delta' and
                        params.get('turnId') == turn_id):
                    delta = params.get('delta')
                    if isinstance(delta, str) and text_size + len(delta) <= MAX_TEXT:
                        text.append(delta); text_size += len(delta)
                if message.get('method') == 'turn/completed':
                    turn = params.get('turn', {})
                    if turn.get('id') == turn_id and turn.get('status') in ('completed', 'interrupted', 'failed'):
                        status = turn['status']
                        break
                if message.get('method') == 'error' and params.get('turnId') == turn_id:
                    status = 'failed'
                    break
            if status == 'timed_out':
                try:
                    self.interrupt()
                except Exception:
                    self.close()
                    raise
                grace = time.monotonic() + 3
                while time.monotonic() < grace:
                    try: message = self.rpc.next_event(timeout=max(.01, grace - time.monotonic()))
                    except queue.Empty: break
                    params = message.get('params', {})
                    turn = params.get('turn', {})
                    if (message.get('method') == 'turn/completed' and params.get('threadId') == self.thread
                            and turn.get('id') == turn_id and turn.get('status') in ('completed','interrupted','failed')):
                        status = turn['status']; break
                if status == 'timed_out':
                    self.close()  # Keep the bucket lease until ProcessTree confirms termination.
            self.last_status = status
            return {'status': status, 'turn_id': turn_id, 'text': ''.join(text), 'report': self.report(turn_id)}
        finally:
            self._collector_lock.release()

    def steer(self, text):
        if self.last_status != 'running' or not self.turn or not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise ValueError('No active turn or invalid steering message')
        return self.rpc.request('turn/steer', {'threadId': self.thread, 'expectedTurnId': self.turn,
            'input': [{'type': 'text', 'text': text, 'text_elements': []}]})

    def followup(self, text):
        with self._operation_lock:
            if self.last_status not in ('completed', 'interrupted', 'failed', 'unverified') or self._collector_lock.locked():
                raise RuntimeError('Prior collector has not released the native session')
            if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                raise ValueError('Bounded user message required')
            result = self.rpc.request('turn/start', {'threadId': self.thread,
                'input': [{'type': 'text', 'text': text, 'text_elements': []}],
                'model': self.model, 'effort': self.effort, 'sandboxPolicy': {'type': 'readOnly'}})
            self.turn = result['turn']['id']
            self.last_status = 'running'
            return {'thread_id': self.thread, 'turn_id': self.turn}

    def interrupt(self):
        if self.turn:
            return self.rpc.request('turn/interrupt', {'threadId': self.thread, 'turnId': self.turn})
        return None

    def report(self, turn_id=None):
        turn_id = turn_id or self.turn
        usage = None
        for event in reversed(self.rpc.events):
            if event.get('method') == 'thread/tokenUsage/updated':
                params = event.get('params', {})
                if params.get('threadId') == self.thread and params.get('turnId') == turn_id:
                    payload = params.get('tokenUsage')
                    usage = payload.get('last') if isinstance(payload, dict) else None
                    break
        allowed = {'inputTokens', 'outputTokens', 'reasoningOutputTokens', 'cachedInputTokens',
                   'cacheWriteInputTokens', 'totalTokens'}
        if usage is not None and (not isinstance(usage, dict) or set(usage) - allowed or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in usage.values())):
            usage = None
        return {'thread_id': self.thread, 'turn_id': self.turn,
                'state': self.last_status, 'usage': usage,
                'usage_note': 'Authoritative last-turn fields only; no inferred totals.'}

    def close(self):
        with self._close_lock:
            if self._closed:
                return
            self.tree.close()
            if self.rpc and self.rpc.proc:
                try:
                    self.rpc.proc.wait(timeout=5)
                except subprocess.TimeoutExpired as error:
                    raise ContainmentError('Native process exit was not verified') from error
                for pipe in (self.rpc.proc.stdin, self.rpc.proc.stdout):
                    if pipe:
                        pipe.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class AcpMetadata:
    """ACP initialize + session/new only; never prompts or claims account entitlement."""
    def __init__(self, argv, project, env, tree=None):
        self.project = str(Path(project).resolve(strict=True))
        self.tree = tree or ProcessTree()
        self.rpc = None
        try:
            self.rpc = Rpc(self.tree, argv, self.project, clean_ai_env(env), timeout=30)
            self.init = self.rpc.request('initialize', {'protocolVersion': 1,
                'clientInfo': {'name': 'store-automation-metadata', 'version': 'proposal'}, 'capabilities': {}})
            self.rpc.notify('initialized')
            self.session = self.rpc.request('session/new', {'cwd': self.project, 'mcpServers': []})
        except BaseException:
            try: self.tree.close()
            except Exception: pass
            raise
        self.session_id = self.session.get('sessionId')

    def report(self):
        config = self.session.get('configOptions', [])
        models, efforts, modes = [], [], []
        if not isinstance(config, list) or len(config) > 100:
            raise ValueError('Invalid bounded ACP config options')
        for item in config:
            if not isinstance(item, dict) or item.get('category') not in ('model', 'thought_level', 'mode'):
                continue
            options = item.get('options', [])
            if not isinstance(options, list) or len(options) > 500:
                raise ValueError('Invalid bounded ACP options')
            for option in options:
                if not isinstance(option, dict): continue
                # ACP may group choices; project only value/name, never arbitrary settings.
                choices = option.get('options', [option])
                if not isinstance(choices, list) or len(choices) > 500:
                    raise ValueError('Invalid grouped ACP choices')
                for choice in choices:
                    if not isinstance(choice, dict): continue
                    value, name = choice.get('value'), choice.get('name')
                    if not isinstance(value, str) or not 1 <= len(value) <= 200: continue
                    if item['category'] == 'model': models.append({'id': value, 'name': name[:160] if isinstance(name,str) else value})
                    elif item['category'] == 'thought_level': efforts.append(value)
                    else: modes.append(value)
        return {'protocol_version': self.init.get('protocolVersion'), 'session_metadata': True,
                'models': models, 'efforts': efforts, 'modes': modes,
                'billing': 'UNVERIFIED', 'quota': None, 'inference': False}

    def prompt(self, text, entitlement_verified=False):
        if not entitlement_verified:
            raise PermissionError('ACP inference stays disabled until official billing and quota are verified')
        if not self.session_id or not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise ValueError('ACP session or bounded prompt is invalid')
        return self.rpc.request('session/prompt', {'sessionId': self.session_id,
            'prompt': [{'type': 'text', 'text': text}]})

    def cancel(self):
        if self.session_id:
            self.rpc.notify('session/cancel', {'sessionId': self.session_id})
        return None


CodexAgent = CodexSession
NativeClient = CodexSession
