"""Owned native workers and authenticated console; no second conversation supervisor."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid

try:
    from . import console, factory, native_agents, sessions, subscriptions
    from . import dispatch as authority
except ImportError:
    import console, factory, native_agents, sessions, subscriptions
    import dispatch as authority


def _leased_followup(row, lease, text):
    lease.__enter__()
    row['lease'] = lease
    try:
        return row['client'].followup(text)
    except BaseException as error:
        try:
            row['client'].close()
        except Exception as cleanup_error:
            row['state'] = 'cleanup_unverified'
            failure = sessions.ContainmentError('Followup cleanup could not be verified')
            lease.__exit__(type(failure), failure, None)
            raise failure from cleanup_error
        lease.__exit__(type(error), error, error.__traceback__)
        row.pop('lease', None)
        row['state'] = 'failed'
        raise


class Controller:
    def __init__(self, project, env=None):
        self.project = Path(project).resolve(strict=True)
        self.env = factory.clean_ai_env(os.environ if env is None else env)
        self.guard = threading.RLock()
        self.dispatch_guard = threading.Lock()
        self.agents = {}
        self.receipts = []
        self.quota = None
        self.inventory = None
        self.selected = None
        self.closed = False
        self.record_path = authority.owned_path(self.project, '.factory/runs/team-controller.json')
        self.lock_path = authority.owned_path(self.project, '.factory/team.lock')
        self.owner = uuid.uuid4().hex
        authority.reconcile_team(self.project)
        try:
            with self.lock_path.open('x', encoding='utf-8') as stream:
                json.dump({'owner': self.owner, 'pid': os.getpid(), 'identity': sessions.process_identity(os.getpid())}, stream)
                stream.flush(); os.fsync(stream.fileno())
        except FileExistsError:
            raise RuntimeError('Owned console exists; reconcile its PID/identity before takeover')
        self.token = secrets.token_urlsafe(32)
        self.server = console.make_server(self.project, {'snapshot': self.snapshot, 'messages': self.messages,
            'message': self.message, 'abort': self.abort}, token=self.token)
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self._save()
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.observer = threading.Thread(target=self._observe, daemon=True)
        self.observer.start()

    def _save(self):
        authority.atomic(self.record_path, {'project': str(self.project), 'pid': os.getpid(),
            'identity': sessions.process_identity(os.getpid()), 'owner': self.owner,
            'url': self.url, 'state': 'STOPPED' if self.closed else 'RUNNING',
            'agents': self._cards(), 'receipts': self.receipts[-100:]})

    def _cards(self):
        cards = [{key: row[key] for key in ('id', 'task', 'role', 'provider', 'model', 'effort', 'state',
                'usage', 'assignment') if key in row} for row in self.agents.values()]
        for card in cards:
            card['control'] = {'message': card['state'] in ('running', 'completed', 'unverified', 'interrupted', 'failed'),
                               'abort': card['state'] == 'running'}
        return cards

    def snapshot(self):
        with self.guard:
            return {'agents': self._cards(), 'selected': self.selected,
                'updated_at': datetime.now(timezone.utc).isoformat(), 'stale': False,
                'native_ui': {'available': True, 'reason': 'Actual native CLI through owned local console'},
                'quota': self.quota, 'director': 'existing conversation',
                'receipts': self.receipts[-30:]}

    def messages(self, identity):
        with self.guard:
            row = self._owned(identity)
            messages = list(row['messages'][-99:])
            if row.get('stream') and row['state'] == 'running':
                messages.append({'role': 'assistant', 'text': row['stream'], 'time': 'live'})
            return messages

    def _owned(self, identity):
        if identity not in self.agents or self.closed:
            raise ValueError('Agent is not owned by selected project/controller')
        return self.agents[identity]

    def _observe(self):
        while not self.closed:
            try:
                codex = subscriptions.codex_metadata(factory.executable, self.env)
                group = next((g for g in codex.get('quota_groups', []) if g.get('name') == 'Codex Models'), None)
                self.quota = {'captured_at': datetime.now(timezone.utc).isoformat(), 'remaining_fraction': subscriptions.remaining(group),
                              'windows': group.get('buckets', []) if group else [], 'observer': 'RUNNING'}
                if subscriptions.reserve_decision('worker', self.quota['remaining_fraction']) != 'READY':
                    for identity, row in list(self.agents.items()):
                        if row['state'] == 'running': self.abort(identity)
                else:
                    for row in list(self.agents.values()):
                        dispatcher = row.get('dispatcher')
                        if row['state'] == 'waiting_quota' and (not dispatcher or not dispatcher.is_alive()):
                            row['state'] = 'queued'
                            dispatcher = threading.Thread(target=self._queued_dispatch, args=(row, row['prompt']), daemon=True)
                            row['dispatcher'] = dispatcher
                            dispatcher.start()
            except (OSError, ValueError, RuntimeError):
                self.quota = {'remaining_fraction': None, 'observer': 'UNAVAILABLE'}
            for _ in range(60):
                if self.closed: return
                time.sleep(1)

    def start(self, contract_path, prompt, provider='codex'):
        with self.guard:
            if self.closed: raise RuntimeError('Controller is closed')
        if provider != 'codex':
            raise ValueError('Only verified live Codex task dispatch; other account adapters remain gated')
        path = factory.trusted_input(contract_path, '.json')
        task = factory.validate_contract(factory.load(path))
        if not set(task['required_capabilities']).issubset({'reasoning', 'source_read'}):
            raise ValueError('Native task capability is not verified')
        snapshot = subscriptions.inventory(factory.run, factory.executable, self.env)
        complexity = authority.required_complexity(task)
        selected = next((r for r in subscriptions.route(snapshot, complexity)['candidates'] if r['provider'] == 'codex'
            and all(task['delegation'][key] in ('auto', r[key]) for key in ('provider', 'model', 'effort'))), None)
        if selected is None:
            raise RuntimeError('WAITING_QUOTA: fresh included native route unavailable')
        assignment_path, record = authority.assignment(self.project, task, selected, factory.digest_file(path), surface='console')
        identity = record['attempt']
        row = {'id': identity, 'task': task['task_id'], 'role': task['persona']['role'],
            'provider': 'codex', 'model': selected['model'], 'effort': selected['effort'], 'state': 'queued',
            'usage': {}, 'control': {'message': True, 'abort': True}, 'messages': [],
            'assignment': str(assignment_path), 'selected': selected, 'record': record, 'task_contract': task,
            'collector': None, 'collecting_turn': None, 'abort_requested': False, 'prompt': prompt}
        dispatcher = threading.Thread(target=self._queued_dispatch, args=(row, prompt), daemon=True)
        with self.guard:
            if self.closed: raise RuntimeError('Controller closed before native assignment')
            self.agents[identity] = row
            self.selected = identity
            self._save()
            row['dispatcher'] = dispatcher
            dispatcher.start()
        return identity

    def _queued_dispatch(self, row, prompt):
        # ponytail: a shared quota percentage has no token reservation API; serialize owned inference.
        with self.dispatch_guard:
            if self.closed: return
            try:
                snapshot = subscriptions.inventory(factory.run, factory.executable, self.env)
                routes = subscriptions.route(snapshot, authority.required_complexity(row['task_contract']))['candidates']
                if not any(all(r[k] == row['selected'][k] for k in ('provider', 'model', 'effort')) for r in routes):
                    row['state'] = 'waiting_quota'
                    self._save(); return
                row['record']['admission_snapshot_at'] = snapshot['captured_at']
                with self.guard:
                    if self.closed: return
                    self._dispatch(row, prompt)
                row['collector'].join()
            except (OSError, ValueError, RuntimeError, TimeoutError):
                if row['state'] != 'cleanup_unverified': row['state'] = 'failed'
                self._save()

    def _dispatch(self, row, prompt):
        identity, task, selected = row['id'], row['task_contract'], row['selected']
        assignment_path, record = Path(row['assignment']), row['record']
        row['state'] = 'starting'
        def spawned(proc):
            record.update(pid=proc.pid, identity=sessions.process_identity(proc.pid), state='CONTAINED')
            authority.atomic(assignment_path, record)
        def public_delta(event):
            client = row.get('client')
            params = event.get('params', {})
            if client and event.get('method') == 'item/agentMessage/delta' and params.get('threadId') == client.thread and params.get('turnId') == client.turn:
                delta = params.get('delta')
                if isinstance(delta, str): row['stream'] = (row.get('stream', '') + delta)[:16000]
        agent = None
        report_instruction = '\nReturn final JSON with fields ' + ', '.join(subscriptions.REPORT_FIELDS) + \
            '; evidence/changed_files/blockers arrays contain strings; usage null. Task=' + task['task_id'] + \
            ', provider=codex, model=' + selected['model'] + ', effort=' + selected['effort'] + \
            ', role=' + task['persona']['role'] + '. State COMPLETED only if the bounded task is done. No tools or shell.'
        lease = authority.admit(selected, self.project, identity)
        acquired = False
        try:
            lease.__enter__()
            acquired = True
            row['lease'] = lease
            agent = native_agents.CodexAgent(factory.executable('codex'), self.project, selected['model'],
                selected['effort'], self.env, before_resume=spawned, on_notification=public_delta)
            row['client'] = agent
            agent.start(prompt + '\nCONTRACT:\n' + json.dumps(task, ensure_ascii=False) + report_instruction,
                        task['context'], task['delegation']['context_budget_chars'], task.get('context_ranges'))
            row['state'] = 'running'
            row['messages'].append({'role': 'user', 'text': prompt, 'time': str(time.time())})
            self._launch_collector(identity, agent.turn, lease)
            self._save()
            return identity
        except BaseException as error:
            try:
                if agent:
                    agent.close()
            except Exception as cleanup_error:
                if acquired:
                    failure = sessions.ContainmentError('Native launch cleanup could not be verified')
                    lease.__exit__(type(failure), failure, None)
                row['state'] = 'cleanup_unverified'
                self._save()
                raise sessions.ContainmentError('Native launch cleanup could not be verified') from cleanup_error
            if acquired:
                lease.__exit__(type(error), error, error.__traceback__)
            row['state'] = 'failed'
            self._save()
            raise

    def _launch_collector(self, identity, turn_id, lease):
        row = self.agents[identity]
        if row.get('collector') and row['collector'].is_alive():
            raise RuntimeError('Previous native collector is still active')
        thread = threading.Thread(target=self._collect, args=(identity, turn_id, lease), daemon=True)
        row['collector'] = thread
        row['collecting_turn'] = turn_id
        row['abort_requested'] = False
        thread.start()

    def _collect(self, identity, turn_id, lease):
        row = self.agents[identity]
        preserve_lease = False
        try:
            result = row['client'].collect(300)
            if result.get('turn_id') not in (None, turn_id):
                raise ValueError('Collector returned a different native turn')
            report = row['client'].report(turn_id)
            raw = report.get('usage') or {}
            if not isinstance(raw, dict):
                raise ValueError('Native usage report is malformed')
            row['usage'] = {out: raw.get(src) for out, src in [('input','inputTokens'), ('output','outputTokens'),
                ('reasoning','reasoningOutputTokens'), ('cache_read','cachedInputTokens'), ('cache_write','cacheWriteInputTokens')]}
            row['messages'].append({'role': 'assistant', 'text': result['text'], 'time': str(time.time())})
            try:
                final = json.loads(result['text'])
                result['task_result'] = final
                row['report'] = authority.checked_report(result, row['task_contract'], row['selected'])
            except (ValueError, TypeError, AttributeError):
                row['report'] = {'status': 'UNVERIFIED', 'reason': 'Invalid typed native report'}
            terminal = result.get('status')
            row['state'] = (terminal if terminal in ('interrupted', 'failed', 'timed_out') else
                            'completed' if terminal == 'completed' and row['report'].get('state') == 'COMPLETED'
                            else 'unverified')
            record = row['record']
            record.update(state=row['state'], usage=row['usage'], report=row['report'], finished_at=time.time())
            output = row['usage'].get('output')
            record['output_budget_overrun'] = max(0, output - record['output_budget_tokens']) if isinstance(output, int) else None
            authority.atomic(Path(row['assignment']), record)
        except sessions.ContainmentError:
            preserve_lease = True
            row['state'] = 'cleanup_unverified'
            row['record'].update(state=row['state'], finished_at=time.time())
            try: authority.atomic(Path(row['assignment']), row['record'])
            except OSError: pass
        except Exception:
            try:
                row['client'].close()
                row['state'] = 'failed'
            except Exception:
                preserve_lease = True
                row['state'] = 'cleanup_unverified'
        finally:
            if row.get('lease') is lease and not preserve_lease:
                row.pop('lease', None)
                lease.__exit__(None, None, None)
            row['collecting_turn'] = None
            self._save()

    def message(self, identity, text):
        with self.guard:
            row = self._owned(identity)
            launched = None
            if row['state'] == 'running':
                if row.get('abort_requested'):
                    raise RuntimeError('Abort is pending; wait for native collector to release the turn')
                row['client'].steer(text)
            elif row['state'] in ('completed', 'interrupted', 'failed', 'unverified'):
                collector = row.get('collector')
                if collector and collector.is_alive():
                    raise RuntimeError('Previous native collector has not released the session')
                snapshot = subscriptions.inventory(factory.run, factory.executable, self.env)
                task = row['task_contract']
                complexity = authority.required_complexity(task)
                candidates = subscriptions.route(snapshot, complexity)['candidates']
                if not any(all(c[k] == row['selected'][k] for k in ('provider','model','effort')) for c in candidates):
                    raise RuntimeError('Followup quota/model route no longer eligible')
                lease = authority.admit(row['selected'], self.project, identity)
                started = _leased_followup(row, lease, text)
                row['state'] = 'running'
                row['stream'] = ''
                launched = (started['turn_id'], lease)
            else: raise ValueError('Agent is not ready for intervention')
            row['messages'].append({'role': 'user', 'text': text, 'time': str(time.time())})
            if launched:
                self._launch_collector(identity, launched[0], launched[1])
            self.receipts.append({'id': uuid.uuid4().hex, 'agent': identity, 'state': 'NATIVE_ACK',
                                  'director': 'PENDING_RECONCILIATION', 'time': time.time()})
            self._save()
            return True

    def abort(self, identity):
        with self.guard:
            row = self._owned(identity)
            if row['state'] != 'running':
                raise ValueError('Only a running native turn can be interrupted')
            if not row.get('abort_requested'):
                row['client'].interrupt()
                row['abort_requested'] = True
            self.receipts.append({'id': uuid.uuid4().hex, 'agent': identity, 'state': 'INTERRUPT_ACK',
                                  'director': 'PENDING_RECONCILIATION', 'time': time.time()})
            self._save(); return True

    def close(self):
        with self.guard:
            self.closed = True
            rows = list(self.agents.values())
        failures = []
        for row in rows:
            try:
                if row.get('client'): row['client'].close()
            except Exception as error: failures.append(error)
            collector = row.get('collector')
            if collector:
                collector.join(timeout=5)
                if collector.is_alive(): failures.append(RuntimeError('Native collector did not stop'))
            dispatcher = row.get('dispatcher')
            if dispatcher:
                dispatcher.join(timeout=30)
                if dispatcher.is_alive(): failures.append(RuntimeError('Native dispatcher did not stop'))
            lease = row.pop('lease', None)
            if lease:
                failure = sessions.ContainmentError('Native termination unverified') if failures else None
                lease.__exit__(type(failure) if failure else None, failure, None)
        self.server.shutdown(); self.server.server_close()
        self._save()
        if failures: raise sessions.ContainmentError('Native cleanup unverified; team lock preserved')
        if json.loads(self.lock_path.read_text())['owner'] == self.owner: self.lock_path.unlink()
