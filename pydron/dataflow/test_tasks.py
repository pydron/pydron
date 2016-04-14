# Copyright (C) 2015 Stefan C. Mueller
import unittest
from pydron.dataflow import tasks, utils
from pydron.dataflow.graph import G, C, T, FINAL_TICK, START_TICK, graph_factory, Tick
import sys

class TestScheduledCallable(unittest.TestCase):
    
    class SchedulerMock(object):
        def __init__(self):
            self.graph = None
            self.inputs = None
        def execute_blocking(self, graph, inputs):
            self.graph = graph
            self.inputs = inputs
            return {'retval':42}
        
    
    def setUp(self):
        self.scheduler = self.SchedulerMock()
        
    def test_no_param(self):
        target = tasks.ScheduledCallable(self.scheduler, "name", "im a graph", [], None, None, tuple())
        
        self.assertEqual(42, target())
        
        self.assertEqual("im a graph", self.scheduler.graph)
        self.assertEqual({}, self.scheduler.inputs)
        
    def test_positional(self):
        target = tasks.ScheduledCallable(self.scheduler, "name", "im a graph", ['a', 'b'], None, None, tuple())
        
        self.assertEqual(42, target(1,2))
        
        self.assertEqual("im a graph", self.scheduler.graph)
        self.assertEqual({'a':1, 'b':2}, self.scheduler.inputs)
        
    def test_args(self):
        target = tasks.ScheduledCallable(self.scheduler, "name", "im a graph", ['a', 'b'], 'args', None, tuple())
        
        self.assertEqual(42, target(1,2,3))
        
        self.assertEqual("im a graph", self.scheduler.graph)
        self.assertEqual({'a':1, 'b':2, 'args':(3,)}, self.scheduler.inputs)
        
    def test_keyword(self):
        target = tasks.ScheduledCallable(self.scheduler, "name", "im a graph", ['a', 'b', 'c'], None, None, tuple())
        
        self.assertEqual(42, target(1,2,c=3))
        
        self.assertEqual("im a graph", self.scheduler.graph)
        self.assertEqual({'a':1, 'b':2, 'c':3}, self.scheduler.inputs)
        
    def test_kwargs(self):
        target = tasks.ScheduledCallable(self.scheduler, "name", "im a graph", ['a', 'b'], None, 'kwargs', tuple())
        
        self.assertEqual(42, target(1,2,c=3))
        
        self.assertEqual("im a graph", self.scheduler.graph)
        self.assertEqual({'a':1, 'b':2, 'kwargs':{'c':3}}, self.scheduler.inputs)
    
        
class TestConstTask(unittest.TestCase):
    
    def test_evaluate(self):
        target = tasks.ConstTask(value=42)
        actual = target.evaluate({})
        self.assertEqual({'value':42}, actual)
        

class TestIfTask(unittest.TestCase):
    
    def test_refine(self):
        
        # t = True
        # if t:
        #     x = 1
        # else:
        #     x = 2
        # return x
        
        g = G(
            T(1, tasks.ConstTask(True)),
            C(1, "value", 2, "$test"),
            T(2, tasks.IfTask(G(
                T(1, tasks.ConstTask(1)),
                C(1, "value", FINAL_TICK, "x")
            ), G(
                T(1, tasks.ConstTask(2)),
                C(1, "value", FINAL_TICK, "x")
            ))),
            C(2, "x", FINAL_TICK, "retval")
        )
        
        target = g.get_task(START_TICK + 2)
        target.refine(g, START_TICK + 2, {"$test":True})
        
        expected = G(
            T(1, tasks.ConstTask(True)),
            T((2,1), tasks.ConstTask(1)),
            C((2,1), "value", FINAL_TICK, "retval")
        )
        
        utils.assert_graph_equal(expected, g)
        
class TestForTask(unittest.TestCase):
    
    def test_refine_body(self):
        # def f(lst, x):
        #     for x in lst:
        #         pass
        #     return x
            
        with graph_factory():
            g = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              C(1, "value", 2, "$iterator"),
              C(START_TICK, "x", 2, "x"),
              T(2, tasks.ForTask(False, False, G("body",
                  C(START_TICK, "$target",1 , "x"),
                  C(START_TICK, "$iterator", 1, "$iterator"),
                  T(1, tasks.ForTask(True, False, G("body"), G("else"))),
                  C(1, "x", FINAL_TICK, "x")
              ), G("else"))),
              C(2, "x", FINAL_TICK, "retval")
            )
            
        target = g.get_task(START_TICK + 2)
        target.refine(g, START_TICK + 2, {"$iterator":iter([1,2,3])})
        
        with graph_factory():
            expected = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              T((2,1,1), tasks.ConstTask(1)),
              C(1, "value", (2,1,2,1), "$iterator"),
              C((2,1,1), "value", (2,1,2,1), "x"),
              T((2,1,2,1), tasks.ForTask(True, False, G("body",
                  C(START_TICK, "$target",1 , "x"),
                  C(START_TICK, "$iterator", 1, "$iterator"),
                  T(1, tasks.ForTask(True, False, G("body"), G("else"))),
                  C(1, "x", FINAL_TICK, "x")
              ), G("else"))),
              C((2,1,2,1), "x", FINAL_TICK, "retval")
            )
            
        utils.assert_graph_equal(expected, g)
        
        
    def test_refine_body_twice(self):
        # def f(lst, x):
        #     for x in lst:
        #         pass
        #     return x
            
        with graph_factory():
            g = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              C(1, "value", 2, "$iterator"),
              C(START_TICK, "x", 2, "x"),
              T(2, tasks.ForTask(False, False, G("body",
                  C(START_TICK, "$target",1 , "x"),
                  C(START_TICK, "$iterator", 1, "$iterator"),
                  T(1, tasks.ForTask(True, False, G("body"), G("else"))),
                  C(1, "x", FINAL_TICK, "x")
              ), G("else"))),
              C(2, "x", FINAL_TICK, "retval")
            )
            
        it = iter([1,2,3])
        
        target_tick = START_TICK + 2
        target = g.get_task(target_tick)
        target.refine(g, target_tick, {"$iterator":it})
        
        target_tick = Tick.parse_tick((2,1,2,1))
        target = g.get_task(target_tick)
        target.refine(g, target_tick, {"$iterator":it})                
        
        with graph_factory():
            expected = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              T((2,1,1), tasks.ConstTask(1)),
              T((2,2,1), tasks.ConstTask(2)),
              C(1, "value", (2,2,2,1), "$iterator"),
              C((2,2,1), "value", (2,2,2,1), "x"),
              T((2,2,2,1), tasks.ForTask(True, False, G("body",
                  C(START_TICK, "$target",1 , "x"),
                  C(START_TICK, "$iterator", 1, "$iterator"),
                  T(1, tasks.ForTask(True, False, G("body"), G("else"))),
                  C(1, "x", FINAL_TICK, "x")
              ), G("else"))),
              C((2,2,2,1), "x", FINAL_TICK, "retval")
            )
            
        utils.assert_graph_equal(expected, g)
        
    def test_refine_body_break(self):
        # def f(lst, x):
        #     for x in lst:
        #         if True:
        #            break
        #     return x
            
        with graph_factory():
            g = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              C(1, "value", 2, "$iterator"),
              C(START_TICK, "x", 2, "x"),
              T(2, tasks.ForTask(False, False, G("body",
                  T(1, tasks.ConstTask(True)),
                  C(1, "value", 2, "$breaked"),
                  C(START_TICK, "$target",2 , "x"),
                  C(START_TICK, "$iterator", 2, "$iterator"),
                  T(2, tasks.ForTask(True, True, G("body"), G("else"))),
                  C(2, "x", FINAL_TICK, "x")
              ), G("else"))),
              C(2, "x", FINAL_TICK, "retval")
            )

            
        target = g.get_task(START_TICK + 2)
        target.refine(g, START_TICK + 2, {"$iterator":iter([1,2,3])})
        
        with graph_factory():
            expected = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask()),
              C(1, "value", (2,1,2,2), "$iterator"),
              T((2,1,1), tasks.ConstTask(1)),
              T((2,1,2,1), tasks.ConstTask(True)),
              C((2,1,1), "value", (2,1,2,2), "x"),
              C((2,1,2,1), "value", (2,1,2,2), "$breaked"),
              T((2,1,2,2), tasks.ForTask(True, True, G("body",
                  T(1, tasks.ConstTask(True)),
                  C(1, "value", 2, "$breaked"),
                  C(START_TICK, "$target",2 , "x"),
                  C(START_TICK, "$iterator", 2, "$iterator"),
                  T(2, tasks.ForTask(True, True, G("body"), G("else"))),
                  C(2, "x", FINAL_TICK, "x")
              ), G("else"))),
              C((2,1,2,2), "x", FINAL_TICK, "retval")
            )
            
        utils.assert_graph_equal(expected, g)
        
        
class TestWhileTask(unittest.TestCase):
    
    def test_refine_body(self):
        # def f(x):
        #     while x:
        #         pass
        #     return x
            
        with graph_factory():
            g = G(
              C(START_TICK, "x", 1, "$test"),
              C(START_TICK, "x", 1, "x"),
              T(1, tasks.WhileTask(False, False, G("body",
                  C(START_TICK, "x", 1 , "$test"),
                  C(START_TICK, "x", 1 , "x"),
                  T(1, tasks.WhileTask(True, False, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )
            
            
        target = g.get_task(START_TICK + 1)
        target.refine(g, START_TICK + 1, {"$test":True})
        
        with graph_factory():
            expected = G(
              C(START_TICK, "x", (1,1,1), "$test"),
              C(START_TICK, "x", (1,1,1), "x"),
              T((1,1,1), tasks.WhileTask(True, False, G("body",
                  C(START_TICK, "x", 1 , "$test"),
                  C(START_TICK, "x", 1 , "x"),
                  T(1, tasks.WhileTask(True, False, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )
            
            
        utils.assert_graph_equal(expected, g)
        
        
    def test_refine_body_twice(self):
        # def f(x):
        #     while x:
        #         pass
        #     return x
            
        with graph_factory():
            g = G(
              C(START_TICK, "x", 1, "$test"),
              C(START_TICK, "x", 1, "x"),
              T(1, tasks.WhileTask(False, False, G("body",
                  C(START_TICK, "x", 1 , "$test"),
                  C(START_TICK, "x", 1 , "x"),
                  T(1, tasks.WhileTask(True, False, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )
            
            
        target = g.get_task(START_TICK + 1)
        target.refine(g, START_TICK + 1, {"$test":True})
        
        target = g.get_task(Tick.parse_tick((1,1,1)))
        target.refine(g, Tick.parse_tick((1,1,1)), {"$test":True})
        
        with graph_factory():
            expected = G(
              C(START_TICK, "x", (1,2,1), "$test"),
              C(START_TICK, "x", (1,2,1), "x"),
              T((1,2,1), tasks.WhileTask(True, False, G("body",
                  C(START_TICK, "x", 1 , "$test"),
                  C(START_TICK, "x", 1 , "x"),
                  T(1, tasks.WhileTask(True, False, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )
            
            
        utils.assert_graph_equal(expected, g)
        
class TestBuiltinTask(unittest.TestCase):
    
    def setUp(self):
        self.call = None
        def dummy(*args):
            self.call = args
            return "abc"
        self.target = tasks.BuiltinCallTask(dummy, 2)
    
    def test_eval_inputs(self):
        self.target.evaluate({"arg0":1, "arg1":2})
        self.assertEqual(self.call, (1,2))
        
    def test_eval_output(self):
        actual = self.target.evaluate({"arg0":1, "arg1":2})
        self.assertEqual({"value":"abc"}, actual)
        
        
DUMMY_GLOBAL = "Hello"
        
class TestReadGlobal(unittest.TestCase):
    
    def setUp(self):
        self.target = tasks.ReadGlobal(__name__)
        
    def test_global(self):
        actual = self.target.evaluate({"var":"DUMMY_GLOBAL"})
        self.assertEqual({"value":"Hello"}, actual)
        
    def test_builtin(self):
        actual = self.target.evaluate({"var":"range"})
        self.assertEqual({"value":range}, actual)