# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.dataflow import graph
from pydron.dataflow.graph import START_TICK, G, T, C
from pydron.dataflow import utils
import pickle

class TestTick(unittest.TestCase):
    
    def test_inc(self):
        inc = graph.START_TICK + 1
        self.assertLess(graph.START_TICK, inc)
        
    def test_inc_2(self):
        inc1 = graph.START_TICK + 1
        inc2 = graph.START_TICK + 2
        self.assertLess(inc1, inc2)
        
    def test_inc_inc(self):
        inc1 = graph.START_TICK + 1
        inc2 = inc1 + 1
        self.assertLess(inc1, inc2)
        
    def test_inc_loop(self):
        t = graph.Tick((0,4), (False, True))
        t += 10
        expected = graph.Tick((0,14), (False, True))
        self.assertEqual(t, expected)
        
    def test_shift_less_than_base(self):
        a = graph.START_TICK
        b = a + 1
        self.assertLess(a, graph.START_TICK << b)
        
    def test_shift_more_than_next(self):
        a = graph.START_TICK
        b = a + 1
        c = a + 2
        self.assertLess(graph.START_TICK << b, c)
        
    def test_shift(self):
        a = graph.Tick((0,1), (False, False))
        b = graph.Tick((0,2), (False, False))
        actual = a << b
        expected = graph.Tick((0,2,1), (False, False, False))
        self.assertEquals(actual, expected)
        
    def test_shift_keeps_order(self):
        a = graph.START_TICK
        b = a + 1
        self.assertLess(graph.START_TICK << b, (graph.START_TICK << b) + 1)
        
    def test_shift_loop(self):
        a = graph.Tick((0,4), (False, True))
        b = graph.Tick((0,10,5), (False, True, False))
        
        actual = a << b
        expected = graph.Tick((0,10,5, 4), (False, True, False, True))
        self.assertEquals(actual, expected)
        
    def test_mark_loop_iteration(self):
        t = graph.Tick((0,10,5), (False, False, False))
        actual = t.mark_loop_iteration()
        expected = graph.Tick((0,10,5), (False, False, True))
        self.assertEquals(actual, expected)
        
    def test_non_loop_elements(self):
        t = graph.Tick((0,10,5,3), (False, True, False, True))
        self.assertEquals((0,5), t.nonloop_elements)
        
    def test_loop_elements(self):
        t = graph.Tick((0,10,5,3), (False, True, False, True))
        self.assertEquals((10, 3), t.loop_elements)
        
    def test_repr_start(self):
        self.assertEqual("START_TICK", repr(graph.START_TICK))
        
    def test_repr_final(self):
        self.assertEqual("FINAL_TICK", repr(graph.FINAL_TICK))
        
    def test_repr_noshift(self):
        self.assertEqual("4", repr(graph.START_TICK + 4))
        
    def test_repr_shift(self):
        self.assertEqual("(10, 4)", repr(graph.START_TICK + 4 << graph.START_TICK + 10))
        
    def test_repr_noshift_loop(self):
        t = graph.Tick((0,4), (False, True))
        self.assertEqual("*4", repr(t))
        
    def test_repr_shift_loop(self):
        t = graph.Tick((0,10,4), (False, True, False))
        self.assertEqual("(*10, 4)", repr(t))
        
    
    def test_parse_start(self):
        self.assertEqual(graph.START_TICK, graph.Tick.parse_tick("START_TICK"))

    def test_parse_final(self):
        self.assertEqual(graph.FINAL_TICK, graph.Tick.parse_tick("FINAL_TICK"))
        
    def test_parse_int(self):
        self.assertEqual(graph.START_TICK + 42, graph.Tick.parse_tick(42))
        
    def test_parse_tuple(self):
        self.assertEqual(graph.START_TICK + 2 << graph.START_TICK + 42, graph.Tick.parse_tick((42, 2)))
        
    def test_parse_str(self):
        expected = graph.Tick((0,1,2,3), (False, False, False, False))
        actual = graph.Tick.parse_tick("1,2,3")
        self.assertEquals(actual, expected)
        
    def test_parse_str_loop(self):
        expected = graph.Tick((0,1,2,3), (False, False, True, False))
        actual = graph.Tick.parse_tick("1,*2,3")
        self.assertEquals(actual, expected)
        
    def assertEqual(self, first, second, msg=None):
        unittest.TestCase.assertEqual(self, first, second, msg=msg)
        if isinstance(first, graph.Tick) and isinstance(second, graph.Tick):
            unittest.TestCase.assertEqual(self, first._loopmask, second._loopmask, msg=msg)
        
    def assertEquals(self, first, second, msg=None):
        self.assertEqual(first, second, msg)
        
class TestGraph(unittest.TestCase):
    
    def setUp(self):
        self.target = graph.Graph()
        self.observer = MockObserver()
    
    def test_pickle(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        s = pickle.dumps(self.target, protocol=pickle.HIGHEST_PROTOCOL)
        copy = pickle.loads(s)
        self.assertEqual(self.target, copy)
    
    def test_add_task(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test'})
        self.assertEqual([START_TICK + 100], list(self.target.get_all_ticks()))
        
    def test_remove_task(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test'})
        self.target.remove_task(START_TICK + 100)
        self.assertEqual([], list(self.target.get_all_ticks()))
        
    def test_get_task_properies(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test'})
        self.assertEqual({'nicename':'test'}, self.target.get_task_properties(START_TICK + 100))
        
    def test_set_task_property(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test'})
        self.target.set_task_property(START_TICK + 100, 'syncpoint', True)
        self.assertEqual({'nicename':'test', 'syncpoint': True}, self.target.get_task_properties(START_TICK + 100))
        
    def test_get_in_connections(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        actual = list(self.target.get_in_connections(START_TICK + 101))
        
        expected = [(graph.Endpoint(START_TICK + 100, 'out'), graph.Endpoint(START_TICK + 101, 'in'))]
        self.assertEqual(actual, expected)
        
    def test_get_out_connections(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        actual = list(self.target.get_out_connections(START_TICK + 100))
        
        expected = [(graph.Endpoint(START_TICK + 100, 'out'), graph.Endpoint(START_TICK + 101, 'in'))]
        self.assertEqual(actual, expected)
        
    def test_disconnect(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        self.target.disconnect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        actual = list(self.target.get_in_connections(START_TICK + 101))
        expected = []
        self.assertEqual(actual, expected)
        
    def test_same_tick(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.assertRaises(ValueError, self.target.add_task, START_TICK + 100, {'nicename':'test2'})
        
    def test_causality(self):
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        
        self.assertRaises(ValueError, self.target.connect, 
                          graph.Endpoint(START_TICK + 101, 'out'), 
                          graph.Endpoint(START_TICK + 100, 'in'))
        
    def test_double_input(self):
        
        self.target.add_task(START_TICK + 100, None, {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, None, {'nicename':'test2'})
        self.target.add_task(START_TICK + 102, None, {'nicename':'test3'})
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                                          graph.Endpoint(START_TICK + 101, 'in'))
        
        self.assertRaises(ValueError, self.target.connect, 
                          graph.Endpoint(START_TICK + 101, 'out'), graph.Endpoint(START_TICK + 101, 'in'))
        
    def test_get_task(self):
        task = object()
        self.target.add_task(START_TICK + 100, task)
        self.assertEquals(task, self.target.get_task(START_TICK + 100))
        
    def test_mocking(self):
        self.target.add_task(START_TICK + 100, "task1", {'nicename':'test1'})
        self.target.add_task(START_TICK + 101, "task2", {'nicename':'test2'})
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        
        expected =  G(
            T(100, 'task1', {'nicename': 'test1'}),
            C(100, 'out', 101, 'in'),
            T(101, 'task2', {'nicename': 'test2'}),
        )

        utils.assert_graph_equal(expected, self.target)
        
    def test_observer_add_task(self):
        self.target.subscribe(self.observer)
        self.target.add_task(START_TICK + 100, "task1", {'nicename':'test1'})
        self.assertEquals([("task_added", START_TICK + 100, "task1", {'nicename':'test1'})], self.observer.calls)
        
    def test_observer_remove_task(self):
        self.target.add_task(START_TICK + 100, "task1")
        self.target.subscribe(self.observer)
        self.target.remove_task(START_TICK + 100)
        self.assertEquals([("task_removed", START_TICK + 100)], self.observer.calls)
        
    def test_observer_connect(self):
        self.target.add_task(START_TICK + 100, "task1")
        self.target.add_task(START_TICK + 101, "task2")
        self.target.subscribe(self.observer)
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        self.assertEquals([("connected", graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))], self.observer.calls)
        
    def test_observer_disconnect(self):
        self.target.add_task(START_TICK + 100, "task1")
        self.target.add_task(START_TICK + 101, "task2")
        
        self.target.connect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        self.target.subscribe(self.observer)
        self.target.disconnect(graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))
        self.assertEquals([("disconnected", graph.Endpoint(START_TICK + 100, 'out'), 
                            graph.Endpoint(START_TICK + 101, 'in'))], self.observer.calls)
        
    def test_observer_set_task_property(self):
        self.target.add_task(START_TICK + 100, "task1")
        self.target.subscribe(self.observer)
        self.target.set_task_property(START_TICK + 100, "foo", "bar")
        self.assertEquals([("task_property_changed", START_TICK + 100, "foo", "bar")], self.observer.calls)
        
class MockObserver(object):
    
    def __init__(self):
        self.calls = []
        
    def __getattr__(self, name):
        def mock(*args):
            self.calls.append((name,) + args)
        return mock
