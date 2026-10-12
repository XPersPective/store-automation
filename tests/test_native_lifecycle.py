"""Mocked regressions for native_lifecycle fixed proposals; expected to pass there."""
import importlib.util
import queue
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tool import native_agents as agents, team
ROOT = Path(__file__).resolve().parents[1]


class FakeTree:
    def __init__(self): self.closed = 0
    def close(self): self.closed += 1


class FakeRpc:
    def __init__(self, events):
        self.events = []
        self.items = queue.Queue()
        for item in events: self.items.put(item)
    def next_event(self, timeout=None): return self.items.get(timeout=timeout)


class NativeLifecycleReview(unittest.TestCase):
    def test_timeout_interrupt_error_still_closes_native_client(self):
        session = agents.CodexSession.__new__(agents.CodexSession)
        session.thread, session.turn = 'thread', 'turn'
        session._collector_lock = threading.Lock()
        session.rpc = type('Rpc', (), {'next_event': lambda *_args, **_kwargs: (_ for _ in ()).throw(queue.Empty())})()
        with patch.object(session, 'interrupt', side_effect=RuntimeError('RPC unavailable')), patch.object(session, 'close') as close:
            with self.assertRaises(RuntimeError): session.collect(1)
        close.assert_called_once()

    def test_uncertain_collect_cleanup_keeps_admission(self):
        controller = team.Controller.__new__(team.Controller)
        class Client:
            def collect(self, _): raise RuntimeError('RPC error')
            def close(self): raise OSError('cannot prove exit')
        lease = unittest.mock.MagicMock()
        row = {'client': Client(), 'state':'running', 'lease':lease, 'collecting_turn':'turn'}
        controller.agents = {'a': row}; controller._save = lambda: None
        controller._collect('a', 'turn', lease)
        self.assertEqual(row['state'], 'cleanup_unverified')
        self.assertIs(row['lease'], lease)
        lease.__exit__.assert_not_called()

    def test_closed_controller_rejects_start_before_discovery(self):
        controller = team.Controller.__new__(team.Controller)
        controller.closed = True; controller.guard = threading.RLock()
        with patch.object(team.subscriptions, 'inventory') as discover:
            with self.assertRaisesRegex(RuntimeError, 'closed'): controller.start('unused', 'unused')
        discover.assert_not_called()

    def test_closed_controller_rejects_message_and_abort_before_rpc(self):
        controller = team.Controller.__new__(team.Controller)
        controller.closed = True; controller.guard = threading.RLock()
        client = unittest.mock.Mock()
        controller.agents = {'a': {'client': client, 'state': 'completed'}}
        with self.assertRaises(ValueError): controller.message('a', 'continue')
        with self.assertRaises(ValueError): controller.abort('a')
        self.assertEqual(client.mock_calls, [])
    def test_constructor_closes_tree_when_rpc_setup_fails(self):
        tree = FakeTree()
        with patch.object(agents, 'Rpc', side_effect=OSError('mock spawn failure')):
            with self.assertRaises(OSError):
                agents.CodexSession('codex', ROOT, 'gpt-6-luna', 'low', {}, tree=tree)
        self.assertEqual(tree.closed, 1)

    def test_collect_discards_wrong_turn_output_and_rejects_second_collector(self):
        session = agents.CodexSession.__new__(agents.CodexSession)
        session.thread, session.turn, session.last_status = 'thread-1', 'turn-2', 'running'
        session._collector_lock = threading.Lock()
        session.rpc = FakeRpc([
            {'method':'item/agentMessage/delta','params':{'threadId':'thread-1','turnId':'turn-1','delta':'stale'}},
            {'method':'item/agentMessage/delta','params':{'threadId':'thread-1','turnId':'turn-2','delta':'current'}},
            {'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-2','status':'completed'}}}])
        session.report = lambda turn_id=None: {'turn_id':turn_id,'usage':None}
        result = session.collect(1)
        self.assertEqual(result['text'], 'current')
        self.assertEqual(result['turn_id'], 'turn-2')

    def test_followup_failure_releases_lease(self):
        class Lease:
            def __init__(self): self.entered = self.exited = 0
            def __enter__(self): self.entered += 1
            def __exit__(self, *exc): self.exited += 1
        class Client:
            def followup(self, _): raise RuntimeError('mock rejected start')
            def close(self): pass
        lease, row = Lease(), {'client':Client(), 'state':'completed'}
        with self.assertRaises(RuntimeError): team._leased_followup(row, lease, 'continue')
        self.assertEqual((lease.entered, lease.exited), (1, 1))
        self.assertNotIn('lease', row)

    def test_invalid_or_blocked_task_report_is_not_completed(self):
        controller = team.Controller.__new__(team.Controller)
        lease = type('Lease', (), {'__exit__': lambda *_: None})()
        row = {'client':type('Client', (), {'collect':lambda *_: {'status':'completed','turn_id':'t','text':'{}'},
              'report':lambda *_: {'usage':None}})(), 'state':'running', 'record':{}, 'assignment':'assignment.json',
              'messages':[], 'task_contract':{}, 'selected':{}, 'lease':lease, 'collecting_turn':'t'}
        controller.agents = {'a':row}
        controller._save = lambda: None
        with patch.object(team.authority, 'checked_report', return_value={'task':'PB-001','state':'BLOCKED'}), \
             patch.object(team.authority, 'atomic'):
            controller._collect('a', 't', lease)
        self.assertEqual(row['state'], 'unverified')


if __name__ == '__main__':
    unittest.main(verbosity=2)
