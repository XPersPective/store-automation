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
        self.assertEqual(json.loads(output[-1])['server'], 'STOPPED')

    def test_live_process_records_structural_events_before_exit_and_timeout(self):
        script = "import json; print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':3}})); print('SECRET_BODY')"
        emitted = []
        result = sessions.stream_run([sys.executable, '-c', script], self.project, dict(os.environ), emit=emitted.append)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['reported_usage']['output'], 3)
        lifecycle = Path(result['lifecycle'])
        record = json.loads(lifecycle.read_text())
        self.assertEqual(record['state'], 'FINISHED')
        self.assertNotIn('SECRET_BODY', lifecycle.read_text())
        self.assertNotIn('SECRET_BODY', lifecycle.with_suffix('.jsonl').read_text())
        self.assertEqual(len(emitted), 1)
        timed = sessions.stream_run([sys.executable, '-c', 'import time; time.sleep(10)'],
                                    self.project, dict(os.environ), timeout=.2)
        self.assertEqual(timed['exit_code'], 124)
        self.assertEqual(json.loads(Path(timed['lifecycle']).read_text())['state'], 'TIMEOUT')


if __name__ == '__main__':
    unittest.main()
