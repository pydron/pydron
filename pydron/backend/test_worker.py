# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.backend import worker
from twisted.internet import defer
from twisted.internet.defer import CancelledError
from remoot import smartstarter, pythonstarter
import anycall
import utwist
from pydron.dataflow import graph
import twistit

TICK1 = graph.START_TICK + 1

class TestWorker(unittest.TestCase):
    
    def setUp(self):
        self.task = MockTask()
        self.target = worker.Worker("myid", "local")
        self.other = worker.Worker("otherid", "local")
    
    def test_set_get_value(self):
        self.target.set_value("x", 123)
        self.assertEqual(123, extract(self.target.get_value("x")))
        
    def test_reduce(self):
        self.target.set_value("x", 123)
        self.assertEqual(246, extract(self.target.reduce("x", lambda x:2*x)))
        
    def test_set_get_cucumber(self):
        self.target.set_cucumber("x", "123")
        self.assertEqual("123", extract(self.target.get_cucumber("x")))
        
    def test_fetch_from(self):
        self.other.set_value("x", 123)
        self.target.fetch_from(self.other, "x")
        self.assertEqual(123, extract(self.target.get_value("x")))

    def test_fetch_from_noreturn(self):
        self.other.set_value("x", 123)
        d = self.target.fetch_from(self.other, "x")
        self.assertNotEqual(123, extract(d), "Fetch should only update the worker, not return the value")
        
    def test_free(self):
        self.target.set_value("x", 123)
        self.target.free("x")
        d = self.target.get_value("x")
        self.assertRaises(KeyError, extract, d)
        
    @utwist.with_reactor
    @twistit.yieldefer
    def test_evaluate_present(self):
        self.target.set_value("x", 123)
        yield self.target.evaluate(TICK1, self.task, {"in": ("x", self.other)})
        self.assertEqual({"in": 123}, self.task.inputs)
        
    @utwist.with_reactor
    @twistit.yieldefer
    def test_evaluate_load(self):
        self.other.set_value("x", 123)
        yield self.target.evaluate(TICK1, self.task, {"in": ("x", self.other)})
        self.assertEqual({"in": 123}, self.task.inputs)
        
    @utwist.with_reactor
    @twistit.yieldefer
    def test_evaluate_present_two(self):
        self.target.set_value("x", 123)
        self.target.set_value("y", 456)
        yield self.target.evaluate(TICK1, self.task, {"in1": ("x", self.other), "in2": ("y", self.other)})
        self.assertEqual({"in1": 123, "in2":456}, self.task.inputs)
        
    @utwist.with_reactor
    @twistit.yieldefer
    def test_evaluate_load_two(self):
        self.other.set_value("x", 123)
        self.other.set_value("y", 456)
        yield self.target.evaluate(TICK1, self.task, {"in1": ("x", self.other), "in2": ("y", self.other)})
        self.assertEqual({"in1": 123, "in2":456}, self.task.inputs)
        
    @utwist.with_reactor
    @twistit.yieldefer
    def test_evaluate_outputs(self):
        self.target.set_value("x", 123)
        actual = yield self.target.evaluate(TICK1, self.task, {"in": ("x", self.other)})
        self.assertIn("out", actual.result)
        actual_value = yield self.target.get_value(actual.result["out"])
        self.assertEqual("Hello", actual_value)
        
class TestValueHolder(unittest.TestCase):
    
    def test_setget(self):
        
        target = worker.ValueHolder("123", None)
        target.set("value")
        d = target.get()
        
        actual = extract(d)
        self.assertEqual("value", actual)
        
    def test_getset(self):
        target = worker.ValueHolder("123", None)
        d = target.get()
        target.set("value")
        
        actual = extract(d)
        self.assertEqual("value", actual)
        
    def test_getgetset(self):
        target = worker.ValueHolder("123", None)
        d1 = target.get()
        d2 = target.get()
        target.set("value")
        
        actual = extract(d1)
        self.assertEqual("value", actual)
        actual = extract(d2)
        self.assertEqual("value", actual)
        
    def test_cancel(self):
        cancelled = defer.Deferred()
        def cancel():
            cancelled.callback(True)
        
        target = worker.ValueHolder("123", cancel)
        d = target.get()
        d.cancel()
        self.assertRaises(CancelledError, extract, d)
        
        actual = extract(cancelled)
        self.assertEqual(True, actual)
        
    def test_cancel2(self):
        cancelled = defer.Deferred()
        def cancel():
            cancelled.callback(True)
        
        target = worker.ValueHolder("123", cancel)
        d1 = target.get()
        d2 = target.get()
        
        d1.cancel()
        self.assertEqual(False, cancelled.called, "Transfer cancelled to early.")
        self.assertRaises(CancelledError, extract, d1)
        
        d2.cancel()
        self.assertRaises(CancelledError, extract, d2)
        
        actual = extract(cancelled)
        self.assertEqual(True, actual)
        
    def test_free(self):
        target = worker.ValueHolder("123", None)
        target.set("123")
        target.free()
        self.assertRaises(ValueError, target.get)
        self.assertIsNone(target._value)
        
    def test_free_cancel(self):
        
        cancelled = defer.Deferred()
        def cancel():
            cancelled.callback(True)
        
        target = worker.ValueHolder("123", cancel)
        f = target.free()
        self.assertRaises(ValueError, target.get)
        self.assertIsNone(target._value)
        self.assertTrue(f.called)
    
        self.assertEqual(True, extract(cancelled))
        
    def test_get_free_set(self):
        target = worker.ValueHolder("123", None)
        d = target.get()
        f = target.free()
        self.assertFalse(f.called)
        target.set("123")
        self.assertEqual("123", extract(d))
        self.assertTrue(f.called)
        
    def test_get_free_set_is_freed(self):
        target = worker.ValueHolder("123", None)
        target.get()
        target.free()
        target.set("123")
        self.assertRaises(ValueError, target.get)
        self.assertIsNone(target._value)
    
    def test_get_free_cancel(self):
        
        cancelled = defer.Deferred()
        def cancel():
            cancelled.callback(True)
        
        target = worker.ValueHolder("123", cancel)
        d = target.get()
        f = target.free()
        
        self.assertFalse(f.called)
        
        d.cancel()
        
        self.assertRaises(CancelledError, extract, d)
        self.assertTrue(f.called)
        self.assertTrue(extract(cancelled))
        
class TestWorkerStarter(unittest.TestCase):
    
    @defer.inlineCallbacks
    def twisted_setup(self):
        starter = pythonstarter.LocalStarter()
        self.rpc = anycall.create_tcp_rpc_system()
        anycall.RPCSystem.default = self.rpc
        
        yield self.rpc.open()
        
        self.smart = smartstarter.SmartStarter(starter, self.rpc, anycall.create_tcp_rpc_system, [])
        self.target = worker.WorkerStarter(self.smart)
        
    @utwist.with_reactor
    @defer.inlineCallbacks
    def test_start_stop(self):
        worker = yield self.target.start()
        
        reset = self.rpc.create_local_function_stub(worker.reset)
        stop = self.rpc.create_local_function_stub(worker.stop)
        
        yield reset()
        yield stop()
        
    @defer.inlineCallbacks
    def twisted_teardown(self):
        yield self.rpc.close()
        
    
    
        
def extract(d):
    """
    Returns the value the given deferred passes to the callback or raises
    the exception passed to errback. If the deferred has no result yet
    a ValueError is raised.
    """
    if not d.called:
        raise ValueError("Deferred not yet called")
    
    failure = []
    value = []
    
    def fail(f):
        failure.append(f)
    
    def success(v):
        value.append(v)
        
    d.addCallbacks(success, fail)
    
    if failure:
        failure[0].raiseException()
    else:
        return value[0]
    
class MockTask(object):
    
    def __init__(self):
        self.inputs = None
    
    def evaluate(self, inputs):
        self.inputs = inputs
        return {"out": "Hello"}