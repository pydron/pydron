# Copyright (C) 2015 Stefan C. Mueller

import unittest

from pydron.dataflow import tasks
from pydron.dataflow.graph import G, T, C, FINAL_TICK, START_TICK, Endpoint, Tick
from pydron.interpreter import traverser
from twisted.internet import defer
from twisted.python import failure
import twistit

TICK1 = START_TICK + 1
TICK2 = START_TICK + 2

class TestTraverser(unittest.TestCase):
    
    def setUp(self):
        
        self.refine = []
        self.ready = []
        
        def refine_task_callback(g, tick, task, inputs):
            self.assertEqual(traverser.TaskState.REFINING, self.target.get_task_state(tick))
            d = defer.Deferred()
            self.refine.append((g, tick, task, inputs, d))
            return d
        
        def ready_task_callback(g, tick, task, inputs):
            self.assertEqual(traverser.TaskState.EVALUATING, self.target.get_task_state(tick))
            d = defer.Deferred()
            self.ready.append((g, tick, task, inputs, d))
            return d
        
        self.target = traverser.Traverser(refine_task_callback, ready_task_callback)
        
    def next_refine(self):
        try:
            return self.refine.pop(0)
        except IndexError:
            return None
    
    def next_ready(self):
        try:
            return self.ready.pop(0)
        except IndexError:
            return None
        
    def test_get_task_state_waiting_for_inputs(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", 2, "in"),
            T(2, "task"),
            C(2, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        self.assertEqual(traverser.TaskState.WAITING_FOR_INPUTS, self.target.get_task_state(TICK2))
        
    def test_get_task_state_evaluating(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", 2, "in"),
            T(2, "task"),
            C(2, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        self.next_ready()[-1].callback(traverser.EvalResult({"value":"Hello"}))
        self.assertEqual(traverser.TaskState.EVALUATING, self.target.get_task_state(TICK2))
        
    def test_get_task_state_evaluated(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", 2, "in"),
            T(2, "task"),
            C(2, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        self.next_ready()[-1].callback(traverser.EvalResult({"value":"Hello"}))
        self.assertEqual(traverser.TaskState.EVALUATED, self.target.get_task_state(TICK1))
        
    def test_get_task_state_refining(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        self.assertEqual(traverser.TaskState.REFINING, self.target.get_task_state(TICK1))

    def test_get_task_state_waiting_for_refiner(self):
        task = MockTask("in")
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", 2, "in"),
            T(2, task),
            C(2, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        self.assertEqual(traverser.TaskState.WAITING_FOR_REFINE_INPUTS, self.target.get_task_state(TICK2))

    def test_no_inputs_task_ready(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        self.assertEqual((TICK1, tasks.ConstTask(None), {}), self.next_ready()[1:-1])
        self.assertEqual(None, self.next_ready())
        
    def test_injest_result(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", 2, "in"),
            T(2, "task"),
            C(2, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        self.next_ready()[-1].callback(traverser.EvalResult({"value":"Hello"}))
        self.assertEqual((TICK2, "task", {"in":"Hello"}), self.next_ready()[1:-1])
        
    def test_finish(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", FINAL_TICK, "retval")
        )
        d = self.target.execute(g, {})
        self.next_ready()[-1].callback(traverser.EvalResult({"value":"Hello"}))
        
        outputs = extract(d)
        self.assertEqual({"retval":"Hello"}, outputs)
        
        
    def test_finish_nomoretasks(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", FINAL_TICK, "retval")
        )
        self.target.execute(g, {})
        
        self.next_ready()[-1].callback({"value":"Hello"})
        
        self.assertIsNone(self.next_ready())
        
    def test_eval_fail(self):
        g = G(
            T(1, tasks.ConstTask(None)),
            C(1, "value", FINAL_TICK, "retval")
        )
        d = self.target.execute(g, {})
        self.next_ready()[-1].errback(failure.Failure(MockError()))
        
        
        f = twistit.extract_failure(d)
        self.assertTrue(f.check(traverser.EvaluationError))
        self.assertTrue(f.value.cause.check(MockError))
        self.assertEqual(Tick.parse_tick(1), f.value.tick)
    
    def test_refine_called(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        self.assertEqual((TICK1, task, {"in": "refinedata"}), self.next_refine()[1:-1])
        
    def test_eval_not_before_refine(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        self.assertEqual(None, self.next_ready())
        
    def test_refine_only_once(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        self.next_refine()[-1].callback(None)
        self.assertEqual(None, self.next_refine())
        
    def test_eval_after_refine(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        self.next_refine()[-1].callback(None)
        self.assertEqual((TICK1, task, {"in":"refinedata"}), self.next_ready()[1:-1])
        
    def test_refine_fail(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        d = self.target.execute(g, {"a": "refinedata"})
        
        self.next_refine()[-1].errback(failure.Failure(MockError()))
        
        f = twistit.extract_failure(d)
        self.assertTrue(f.check(traverser.RefineError))
        self.assertTrue(f.value.cause.check(MockError))
        self.assertEqual(Tick.parse_tick(1), f.value.tick)
        
    def test_refine_removes_task(self):
        task = MockTask("in")
        g = G(
            C(START_TICK, "a", 1, "in"),
            T(1, task),
            C(1, "out", FINAL_TICK, "retval")
        )
        self.target.execute(g, {"a": "refinedata"})
        
        refine_g, _, _, _, refine_d = self.next_refine()
        refine_g.disconnect(Endpoint(START_TICK, "a"), Endpoint(TICK1, "in"))
        refine_g.disconnect(Endpoint(TICK1, "out"), Endpoint(FINAL_TICK, "retval"))
        refine_g.remove_task(TICK1)
        refine_d.callback(None)
        
        self.assertEqual(None, self.next_refine())
        
        
class MockError(Exception):
    pass
        
class MockTask(object):
    def __init__(self, *refiner_ports):
        self.refiner_ports = set(refiner_ports)

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