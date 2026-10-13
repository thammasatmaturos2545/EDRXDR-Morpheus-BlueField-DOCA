"""Offline contract tests; extract cleanup only, without importing GPU libraries."""
import ast
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

class ShutdownTests(unittest.TestCase):
    def setup_function(self):
        source=Path(__file__).with_name('worker.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='close_consumers')
        events=[]
        watchdog=Mock()
        scope={'audit':lambda kind,**fields:events.append((kind,fields)),
               'faulthandler':watchdog,'sys':sys,'time':time}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'cleanup','exec'),scope)
        return scope['close_consumers'],events,watchdog

    def test_success_records_every_close_in_order(self):
        close,events,watchdog=self.setup_function()
        clients=[Mock(),Mock(),Mock()]
        close(clients)
        self.assertEqual([e[0] for e in events],['shutdown_begin',
            'consumer_close_begin','consumer_close_done',
            'consumer_close_begin','consumer_close_done',
            'consumer_close_begin','consumer_close_done','consumer_cleanup_complete'])
        self.assertEqual([e[1]['role'] for e in events if e[0]=='consumer_close_done'],['capture','score','index'])
        for client in clients: client.close.assert_called_once_with()
        watchdog.dump_traceback_later.assert_called_once_with(20,repeat=True,file=sys.stderr)
        watchdog.cancel_dump_traceback_later.assert_not_called()

    def test_failure_not_success_and_remaining_consumers_closed(self):
        close,events,_=self.setup_function()
        clients=[Mock(),Mock(),Mock()]
        clients[0].close.side_effect=RuntimeError('private details')
        with self.assertRaises(RuntimeError): close(clients)
        for client in clients: client.close.assert_called_once_with()
        self.assertNotIn('consumer_cleanup_complete',[e[0] for e in events])
        self.assertNotIn('private details',str(events))

    def test_partial_initialization(self):
        close,events,_=self.setup_function()
        close([Mock()])
        self.assertEqual(events[0][1]['consumer_count'],1)
        self.assertEqual(events[-1][0],'consumer_cleanup_complete')

    def test_no_clients(self):
        close,events,_=self.setup_function()
        close([])
        self.assertEqual([e[0] for e in events],['shutdown_begin','consumer_cleanup_complete'])

if __name__=='__main__': unittest.main(verbosity=2)
