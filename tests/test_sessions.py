import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from tool import sessions


class SessionChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve()
        self.env = {'OPENCODE_CONFIG_CONTENT': '{}'}

    def record(self, **overrides):
        data = {'project': str(self.project), 'pid': 123, 'identity': {'birth': '1', 'image': 'C:/native/opencode.exe'},
                'binary': 'C:/native/opencode.exe', 'url': 'http://127.0.0.1:12345', 'state': 'RUNNING',
                'config_sha256': sessions.config_digest(self.env)}
        data['terminal_window'] = 'store-' + 'a' * 32
        data.update(overrides)
        sessions.store(self.project, data)
        return data

    def test_project_filter_and_attach_reject_cross_project_session(self):
        rows = [{'id': 'ses_mine', 'directory': str(self.project)},
                {'id': 'ses_foreign', 'directory': str(self.project.parent)},
                {'id': '../../escape', 'directory': str(self.project)}, {'id': 7}]
        self.assertEqual([r['id'] for r in sessions.project_sessions(self.project, rows)], ['ses_mine'])
        data = self.record()
        with patch.object(sessions, 'process_identity', return_value=data['identity']), \
             patch.object(sessions, 'api', return_value=rows):
            with self.assertRaisesRegex(ValueError, 'not owned'):
                sessions.attach_command(self.project, self.env, 'ses_foreign')
            self.assertEqual(sessions.attach_command(self.project, self.env, 'ses_mine')[-2:], ['--session', 'ses_mine'])
        self.record(project=str(self.project.parent))
        with self.assertRaisesRegex(ValueError, 'another project'):
            sessions.load_state(self.project)

    def test_stop_rejects_pid_reuse_or_foreign_endpoint(self):
        self.record()
        with patch.object(sessions, 'process_identity', return_value={'birth': '2', 'image': 'owned'}), \
             patch.object(subprocess, 'run') as signal:
            with self.assertRaisesRegex(RuntimeError, 'PID was reused'):
                sessions.stop(self.project)
            signal.assert_not_called()
        self.record(url='http://other.example:1234')
        with self.assertRaisesRegex(ValueError, 'loopback'):
            sessions.load_state(self.project)

    def test_password_required_and_never_persisted(self):
        with self.assertRaisesRegex(ValueError, 'password'):
            sessions.start(self.project, sys.executable, {})
        self.assertFalse(sessions.state_path(self.project).exists())

    def test_start_storage_failure_closes_owned_process_tree(self):
        tree = MagicMock()
        tree.spawn.return_value.pid = 123
        env = dict(self.env, OPENCODE_SERVER_PASSWORD='synthetic-local-test')
        with patch.object(sessions, 'ProcessTree', return_value=tree), \
             patch.object(sessions, 'process_identity', return_value={'birth': '1', 'image': 'owned'}), \
             patch.object(sessions, 'store', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):
                sessions.start(self.project, sys.executable, env)
        tree.close.assert_called_once()
        self.assertFalse(sessions.state_path(self.project).with_suffix('.lock').exists())

    def test_attach_rejects_permission_overlay_mismatch(self):
        data = self.record()
        with patch.object(sessions, 'process_identity', return_value=data['identity']):
            with self.assertRaisesRegex(ValueError, 'permissions differ'):
                sessions.attach_command(self.project, {'OPENCODE_CONFIG_CONTENT': '{"edit":"allow"}'})

    def test_watcher_opens_active_native_sessions_without_duplicate_panes(self):
        current = {'sessions': [{'id': 'ses_worker', 'state': 'busy'}, {'id': 'ses_reviewer', 'state': 'idle'}]}
        with patch.object(sessions, 'status', return_value=current), \
             patch.object(sessions, 'attach') as attach, \
             patch.object(sessions.time, 'sleep', side_effect=[None, KeyboardInterrupt]):
            result = sessions.watch(self.project, self.env, emit=lambda value: None, auto_panes=True)
        self.assertEqual(result['state'], 'WATCH_CLOSED')
        self.assertEqual(attach.call_count, 2)
        self.assertEqual(attach.call_args_list[0].args[2], 'ses_worker')

    def test_status_excludes_previous_runs_and_foreign_projects(self):
        data = self.record(started_at=100)
        rows = [{'id': 'ses_current', 'directory': str(self.project), 'time': {'created': 100001}},
                {'id': 'ses_previous', 'directory': str(self.project), 'time': {'created': 99999}},
                {'id': 'ses_foreign', 'directory': str(self.project.parent), 'time': {'created': 100001}}]
        def api(project, state, env, endpoint):
            return rows if endpoint == '/session' else ({'ses_current': {'type': 'busy'}} if endpoint == '/session/status' else [])
        with patch.object(sessions, 'process_identity', return_value=data['identity']), patch.object(sessions, 'api', side_effect=api):
            current = sessions.status(self.project, self.env)
        self.assertEqual([row['id'] for row in current['sessions']], ['ses_current'])
        self.assertEqual(current['sessions'][0]['state'], 'busy')

    def test_state_update_ignores_planted_predictable_temp_file(self):
        path = sessions.state_path(self.project).with_suffix('.tmp')
        path.write_text('untouched')
        self.record()
        self.assertEqual(path.read_text(), 'untouched')

    def test_usage_unknown_and_real_zero(self):
        self.assertIsNone(sessions.normalize_usage({})['input'])
        usage = sessions.normalize_usage({'tokens': {'input': 0, 'output': 4,
                                                  'reasoning': -1, 'cache': {'read': True}}, 'cost': 0})
        self.assertEqual(usage['input'], 0)
        self.assertEqual(usage['output'], 4)
        self.assertEqual(usage['reported_cost'], 0)
        self.assertIsNone(usage['reasoning'])
        self.assertIsNone(usage['cache_read'])
        self.assertIsNone(sessions.normalize_usage({'cost': float('inf')})['reported_cost'])
        events = '\n'.join(json.dumps(e) for e in [
            {'type': 'turn.completed', 'usage': {'input_tokens': 3, 'output_tokens': 5, 'cached_input_tokens': 1}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 7, 'output_tokens': 2, 'cached_input_tokens': 0}}])
        self.assertEqual(sessions.reported_usage(events)['input'], 10)
        self.assertIsNone(sessions.reported_usage(events)['reported_cost'])

    def test_public_summary_never_contains_content(self):
        event = {'type': 'tool_use', 'sessionID': 'ses_mine', 'part': {'tool': 'read',
                 'state': {'status': 'completed', 'input': {'password': 'SENSITIVE'},
                           'output': 'SENSITIVE', 'metadata': {'sessionId': 'ses_child'}}}}
        public = sessions.public_event(event)
        self.assertEqual(public['child_session'], 'ses_child')
        self.assertNotIn('SENSITIVE', json.dumps(public))
        self.assertIsNone(sessions.public_event({'type': 'text', 'part': {'text': 'SENSITIVE'}}))
        self.assertIsNone(sessions.public_event([]))
        self.assertEqual(sessions.public_event({'type': 'step_finish', 'part': []})['usage'],
                         sessions.normalize_usage({}))

    def test_terminal_argv_preserves_spaces_without_shell_and_rejects_separator(self):
        argv = ['C:/Program Files/Native/opencode.exe', 'attach', 'http://127.0.0.1:1234',
                '--dir', str(self.project / 'my app')]
        data = self.record()
        with patch.object(sessions.shutil, 'which', return_value='C:/Windows/wt.exe'), \
             patch.object(sessions, 'process_identity', return_value=data['identity']):
            command = sessions.terminal_command(self.project, argv)
            self.assertEqual(command[-len(argv):], argv)
            self.assertNotIn('powershell', command)
            with self.assertRaises(ValueError):
                sessions.terminal_command(self.project, argv + ['x;new-tab'])

    def test_timeout_and_success_kill_delayed_child_mutators(self):
        for parent_wait in (True, False):
            marker = self.project / ('timeout-marker' if parent_wait else 'success-marker')
            child = 'import time; from pathlib import Path; time.sleep(.8); Path(' + repr(str(marker)) + ').write_text("BAD")'
            parent = ('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + '],'
                      'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); ' + ('time.sleep(10)' if parent_wait else 'pass'))
            result = sessions.stream_run([sys.executable, '-c', parent], self.project, dict(os.environ),
                                         timeout=.5 if parent_wait else 3)
            self.assertEqual(result['exit_code'], 124 if parent_wait else 0)
            time.sleep(1)
            self.assertFalse(marker.exists(), 'owned child survived parent dispatch completion')

    def test_watch_stopped_server_returns_clean_lifecycle_end(self):
        self.record(state='STOPPED')
        output = []
        with patch.object(sessions, 'status', side_effect=RuntimeError('owned server stopped')), \
             patch.object(sessions, 'process_identity', return_value=None):
            result = sessions.watch(self.project, self.env, emit=output.append)
        self.assertEqual(result['state'], 'WATCH_CLOSED')
        self.assertIn('İzleme kapandı', output[-1])

    def test_live_process_records_structural_events_before_exit_and_timeout(self):
        script = "import json; print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':3}})); print('SECRET_BODY')"
        emitted = []
        result = sessions.stream_run([sys.executable, '-c', script], self.project, dict(os.environ),
                                     emit=emitted.append, metadata={'language': 'en', 'role': 'factory-reviewer', 'model': 'native-test'})
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['reported_usage']['output'], 3)
        lifecycle = Path(result['lifecycle'])
        record = json.loads(lifecycle.read_text())
        self.assertEqual(record['state'], 'FINISHED')
        self.assertEqual(record['language'], 'en')
        self.assertEqual(result['role'], 'factory-reviewer')
        self.assertEqual(result['model'], 'native-test')
        self.assertEqual(result['language'], 'en')
        self.assertNotIn('SECRET_BODY', lifecycle.read_text())
        self.assertNotIn('SECRET_BODY', lifecycle.with_suffix('.jsonl').read_text())
        self.assertEqual(len(emitted), 1)
        timed = sessions.stream_run([sys.executable, '-c', 'import time; time.sleep(10)'],
                                    self.project, dict(os.environ), timeout=.2)
        self.assertEqual(timed['exit_code'], 124)
        self.assertEqual(json.loads(Path(timed['lifecycle']).read_text())['state'], 'TIMEOUT')

    def test_human_roles_usage_and_language_do_not_render_private_fields(self):
        data = {'server': 'RUNNING', 'sessions': [
            {'id': 'ses_manager', 'agent': 'factory', 'state': 'busy', 'model': 'opencode/free',
             'usage': {'input': 0, 'output': 7}, 'content': 'SECRET_PROMPT'},
            {'id': 'ses_worker', 'parent': 'ses_manager', 'agent': 'factory-worker', 'state': 'idle',
             'tools': [{'tool': 'read', 'state': 'completed', 'output': 'SECRET_BODY'}]},
            {'id': 'ses_review', 'agent': 'factory-reviewer', 'state': 'busy', 'reasoning': 'SECRET_REASONING'},
        ]}
        tr = sessions.format_public(data)
        for expected in ('Yönetici', 'Uygulayıcı', 'İnceleyen', 'Çalışıyor', 'Bekliyor',
                         'ses_worker', 'ses_manager', 'Token giriş/çıkış: 0/7', 'Kalan kota: bilinmiyor'):
            self.assertIn(expected, tr)
        en = sessions.format_public(data, 'en')
        for expected in ('Manager', 'Implementer', 'Reviewer', 'Tokens in/out: 0/7', 'Remaining quota: unknown'):
            self.assertIn(expected, en)
        for output in (tr, en):
            self.assertNotIn('SECRET', output)
        self.assertIn('bilinmiyor', sessions.format_public({'usage': {'input': True, 'output': float('nan')}}))
        self.assertEqual(sessions.role_name({'private': 'SECRET'}), 'Ajan')
        history = sessions.format_public({'runs': [{'role': 'worker', 'state': 'FINISHED',
            'native_sessions': ['ses_parent', 'ses_child'], 'exit_code': 0,
            'latest': {'tool': 'edit', 'state': 'completed', 'output': 'SECRET'}}]})
        for expected in ('Çalıştırmalar', 'Uygulayıcı', 'ses_parent', 'ses_child', 'Araç: edit', 'Çıkış kodu: 0'):
            self.assertIn(expected, history)
        self.assertNotIn('SECRET', history)
        with self.assertRaises(ValueError):
            sessions.format_public(data, 'fr')

    def test_watcher_persists_selected_language_in_panes_and_explicit_json(self):
        current = {'language': 'en', 'server': 'RUNNING', 'sessions': [
            {'id': 'ses_worker', 'agent': 'factory-worker', 'state': 'busy'}]}
        outputs = []
        with patch.object(sessions, 'status', return_value=current), \
             patch.object(sessions, 'attach') as attach, \
             patch.object(sessions.time, 'sleep', side_effect=KeyboardInterrupt):
            result = sessions.watch(self.project, self.env, emit=outputs.append, auto_panes=True)
        self.assertIn('Implementer', outputs[0])
        self.assertEqual(result['language'], 'en')
        self.assertEqual(attach.call_args.kwargs['language'], 'en')
        self.assertEqual(attach.call_args.kwargs['role'], 'factory-worker')
        outputs.clear()
        with patch.object(sessions, 'status', return_value=current), \
             patch.object(sessions.time, 'sleep', side_effect=KeyboardInterrupt):
            sessions.watch(self.project, self.env, emit=outputs.append, json_output=True)
        self.assertEqual(json.loads(outputs[0]), current)

    def test_event_output_is_structural_and_terminal_titles_are_localized(self):
        output = sessions.format_public({'event': 'tool_use', 'session': 'ses_parent',
            'child_session': 'ses_child', 'role': 'worker', 'tool': 'task', 'state': 'completed',
            'output': 'SECRET_BODY'})
        self.assertIn('Uygulayıcı', output)
        self.assertIn('ses_child', output)
        self.assertNotIn('SECRET', output)
        data = self.record()
        with patch.object(sessions.shutil, 'which', return_value='C:/Windows/wt.exe'), \
             patch.object(sessions, 'process_identity', return_value=data['identity']):
            command = sessions.terminal_command(self.project, ['native'], role='factory-reviewer')
            self.assertEqual(command[command.index('--title') + 1], 'İnceleyen')
            command = sessions.terminal_command(self.project, ['native'], role='factory-worker', language='en')
            self.assertEqual(command[command.index('--title') + 1], 'Implementer')
        with patch.object(sessions, 'attach_command', return_value=['native', '--session', 'ses_review']), \
             patch.object(sessions, 'load_state', return_value={'language': 'tr'}), \
             patch.object(sessions, 'status', return_value={'sessions': [{'id': 'ses_review', 'agent': 'factory-reviewer'}]}), \
             patch.object(sessions, 'terminal_command', return_value=['wt.exe']) as terminal, \
             patch.object(sessions.subprocess, 'run'):
            sessions.attach(self.project, self.env, 'ses_review', pane=True)
        self.assertEqual(terminal.call_args.kwargs['role'], 'factory-reviewer')
        self.assertEqual(terminal.call_args.kwargs['language'], 'tr')

    def test_process_success_never_implies_task_acceptance(self):
        result = {'classification': 'SUCCESS', 'exit_code': 0,
                  'reported_usage': {'input': 2, 'output': 3},
                  'task_result': {'status': 'BLOCKED', 'reason': 'SECRET_PROVIDER_MESSAGE'}}
        tr = sessions.format_public(result)
        self.assertIn('Süreç: Başarıyla sona erdi', tr)
        self.assertIn('Ajan beyanı: Engellendi', tr)
        self.assertIn('Görev kabulü: ayrı doğrulama ve inceleme gerekiyor', tr)
        self.assertIn('Token giriş/çıkış: 2/3', tr)
        self.assertNotIn('SECRET', tr)
        result['task_result'] = {'verdict': 'PASS'}
        en = sessions.format_public(result, 'en')
        self.assertIn('Agent report: Passed', en)
        self.assertIn('Task acceptance: separate verification and review required', en)
        result['task_result'] = {'status': {'private': 'SECRET'}}
        self.assertIn('Agent report: Unknown', sessions.format_public(result, 'en'))
        history = {'runs': [{'language': 'en', 'state': 'FINISHED', 'role': 'worker'}]}
        self.assertIn('Implementer', sessions.format_public(history))
        self.assertIn('Uygulayıcı', sessions.format_public(history, 'tr'))


if __name__ == '__main__':
    unittest.main()
