"""Mocked regressions for native_lifecycle fixed proposals; expected to pass there."""
import importlib.util
import queue
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tool import native_agents as agents
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




if __name__ == '__main__':
    unittest.main(verbosity=2)
