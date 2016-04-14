# Copyright (C) 2015 Stefan C. Mueller

import unittest

from pydron.interpreter import graphdecorator
from pydron.dataflow import graph


TICK1 = graph.START_TICK + 1
TICK2 = graph.START_TICK + 2
TICK3 = graph.START_TICK + 3
TICK4 = graph.START_TICK + 4
TICK5 = graph.START_TICK + 5
FINAL = graph.FINAL_TICK

class TestDataDecorator(unittest.TestCase):
    
    def setUp(self):
        self.target = graphdecorator.DataGraphDecorator(graph.Graph())

    def test_get_data(self):
        self.target.add_task(graph.START_TICK + 1, "task1")
        self.target.set_output_data(graph.START_TICK + 1, {"out1": "data1", "out2":"data2"})
        actual = self.target.get_data(graph.Endpoint(graph.START_TICK + 1, "out1"))
        self.assertEqual("data1", actual)
        
    def test_get_nonexistent_data(self):        
        self.target.add_task(graph.START_TICK + 1, "task1")
        self.target.set_output_data(graph.START_TICK + 1, {"out1": "data1", "out2":"data2"})
        self.assertRaises(KeyError, self.target.get_data, graph.Endpoint(graph.START_TICK + 1, "out3"))
        
    def no_data(self):
        self.target.add_task(TICK1, "task1")
        self.assertRaises(KeyError, self.target.get_data, graph.Endpoint(TICK1, "out"))
                
    def test_graph_input(self):
        self.target.add_task(TICK1, MockTask("in"))
        self.target.connect(graph.Endpoint(graph.START_TICK, "graphin"), graph.Endpoint(TICK1, "in"))
        self.assertRaises(KeyError, self.target.get_data, graph.Endpoint(graph.START_TICK, "graphin"))
        
class TestReadyDecorator(unittest.TestCase):
    
    
    def setUp(self):
        self.target = graphdecorator.ReadyDecorator(
                            graphdecorator.DataGraphDecorator(graph.Graph()))
        
    def test_add_task_flush(self):
        self.target.add_task(TICK1, "task")
        
        actual = self.target.collect_ready_tasks()
        expected = {TICK1, FINAL}
        
        self.assertEqual(actual, expected)
        
    def test_remove_task_after_flush(self):
        self.target.add_task(TICK1, "task")
        
        self.target.collect_ready_tasks()
        self.target.remove_task(TICK1)
        
        actual = self.target.collect_ready_tasks()
        expected = set()
        
        self.assertEqual(actual, expected)
        
    def test_add_conn_before_flush(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))

        actual = self.target.collect_ready_tasks()
        expected = {FINAL, TICK1}
        
        self.assertEqual(actual, expected)
        
    def test_disconnect_before_flush(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.target.disconnect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        
        actual = self.target.collect_ready_tasks()
        expected = {TICK1, TICK2, FINAL}
        
        self.assertEqual(actual, expected)
        
    def test_add_conn_after_flush(self):
        self.target.add_task(graph.START_TICK + 1, "task1")
        self.target.add_task(graph.START_TICK + 2, "task2")
        
        self.target.collect_ready_tasks()
        
        self.target.connect(graph.Endpoint(graph.START_TICK + 1, "out"), 
                          graph.Endpoint(graph.START_TICK + 2, "in"))
        self.target.set_output_data(graph.START_TICK + 1, {"out": "data"})
        
        self.assertEqual(set(), self.target.collect_ready_tasks())
        
    
    def test_set_output_data(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))

        self.target.set_output_data(TICK1, {"out": "data"})
        
        actual = self.target.collect_ready_tasks()
        expected = {TICK1, TICK2, FINAL}
        
        self.assertEqual(actual, expected)
        
    def test_set_output_data_final(self):
        self.target.add_task(TICK1, "task1")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(FINAL, "in"))
        
        self.assertEqual({TICK1}, self.target.collect_ready_tasks())
        
        self.target.set_output_data(TICK1, {"out": "data"})
        
        self.assertEqual({FINAL}, self.target.collect_ready_tasks())
        
        
    def test_set_data_before_connection(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.set_output_data(TICK1, {"out": "data"})
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        actual = self.target.collect_ready_tasks()
        expected = {TICK1, TICK2, FINAL}
        self.assertEqual(actual, expected)
        
    def test_overwrite_data(self):
        self.target.add_task(graph.START_TICK + 1, "task1")
        self.target.set_output_data(graph.START_TICK + 1, {"out1": "data1", "out2":"data2"})
        self.assertRaises(ValueError, self.target.set_output_data, graph.START_TICK + 1, {"out2":"data2"})
        
    def test_syncpoint_only_before(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.add_task(TICK3, "task3", {"syncpoint":True})
        self.target.add_task(TICK4, "task4")
        self.target.add_task(TICK5, "task4")
        self.assertEqual({TICK1, TICK2}, self.target.collect_ready_tasks())
        
    def test_syncpoint_alone(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.add_task(TICK3, "task3", {"syncpoint":True})
        self.target.add_task(TICK4, "task4")
        self.target.add_task(TICK5, "task4")
        
        self.target.collect_ready_tasks()
        self.target.set_output_data(TICK1, {})
        self.target.set_output_data(TICK2, {})
        
        self.assertEqual({TICK3}, self.target.collect_ready_tasks())
        
    def test_syncpoint_after(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.add_task(TICK3, "task3", {"syncpoint":True})
        self.target.add_task(TICK4, "task4")
        self.target.add_task(TICK5, "task4")
        
        self.target.collect_ready_tasks()
        self.target.set_output_data(TICK1, {})
        self.target.set_output_data(TICK2, {})
        self.target.collect_ready_tasks()
        self.target.set_output_data(TICK3, {})
        
        self.assertEqual({TICK4, TICK5, FINAL}, self.target.collect_ready_tasks())
        
    def test_syncpoint_remove(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.add_task(TICK3, "task3", {"syncpoint":True})
        self.target.add_task(TICK4, "task4")
        self.target.add_task(TICK5, "task4")
        self.target.set_task_property(TICK3, "syncpoint", False)
        self.assertEqual({TICK1, TICK2, TICK3, TICK4, TICK5, FINAL}, self.target.collect_ready_tasks())
        
    def test_unrefined(self):
        self.target.add_task(TICK1, MockTask("in"))
        self.assertEqual({FINAL}, self.target.collect_ready_tasks())
        
    def test_refined_initially(self):
        self.target.add_task(TICK1, MockTask("in"), {"refined": True})
        self.assertEqual({TICK1, FINAL}, self.target.collect_ready_tasks())
        
    def test_refined_later(self):
        self.target.add_task(TICK1, MockTask("in"))
        self.assertEqual({FINAL}, self.target.collect_ready_tasks())
        self.target.set_task_property(TICK1, "refined", True)
        self.assertEqual({TICK1}, self.target.collect_ready_tasks())
        
    def test_graph_input(self):
        self.target.add_task(TICK1, MockTask("in"))
        self.target.connect(graph.Endpoint(graph.START_TICK, "graphin"), graph.Endpoint(TICK1, "in"))
        self.assertEqual({FINAL}, self.target.collect_ready_tasks())
        
    def test_was_collected_inqueue(self):
        self.target.add_task(TICK1, "task")
        self.assertFalse(self.target.was_ready_collected(TICK1))
        
    def test_was_collected_true(self):
        self.target.add_task(TICK1, "task")
        self.target.collect_ready_tasks()
        self.assertTrue(self.target.was_ready_collected(TICK1))

    def test_was_collected_not_ready(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertFalse(self.target.was_ready_collected(TICK2))
        
class TestRefineDecorator(unittest.TestCase):
    
    
    def setUp(self):
        self.target = graphdecorator.RefineDecorator(
                            graphdecorator.DataGraphDecorator(graph.Graph()))
        
    def test_add_task_disconnected(self):
        self.target.add_task(TICK1, MockTask("in"))
        self.assertEquals(set(), self.target.collect_refine_tasks())
        
    def test_connect_no_data(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertEquals(set(), self.target.collect_refine_tasks())
        
    def test_set_data_after_connect(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.target.set_output_data(TICK1, {"out": "data"})
        self.assertEquals({TICK2}, self.target.collect_refine_tasks())
        
    def test_set_data_before_connect(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.set_output_data(TICK1, {"out": "data"})
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertEquals({TICK2}, self.target.collect_refine_tasks())
        
    def test_disconnect(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.set_output_data(TICK1, {"out": "data"})
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.target.disconnect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertEquals(set(), self.target.collect_refine_tasks())
        
    def test_disconnect_two(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in1", "in2"))
        self.target.set_output_data(TICK1, {"out": "data"})
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in1"))
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in2"))
        self.target.disconnect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in1"))
        self.assertEquals({TICK2}, self.target.collect_refine_tasks())

    def test_was_collected_inqueue(self):
        self.target.add_task(TICK1, "task")
        self.assertFalse(self.target.was_refine_collected(TICK1))
        
    def test_was_collected_no_refiner_ports(self):
        self.target.add_task(TICK1, "task")
        self.target.collect_refine_tasks()
        self.assertFalse(self.target.was_refine_collected(TICK1))
        
    def test_was_collected_true(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.target.set_output_data(TICK1, {"out": "data"})
        self.target.collect_refine_tasks()
        self.assertTrue(self.target.was_refine_collected(TICK2))

    def test_was_collected_not_ready(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, "task2")
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertFalse(self.target.was_refine_collected(TICK2))
        
    def test_will_be_refined(self):
        self.target.add_task(TICK1, "task1")
        self.target.add_task(TICK2, MockTask("in"))
        self.target.connect(graph.Endpoint(TICK1, "out"), graph.Endpoint(TICK2, "in"))
        self.assertTrue(self.target.will_be_refined(TICK2))
        
    def test_will_not_be_refined(self):
        self.target.add_task(TICK1, "task")
        self.assertFalse(self.target.will_be_refined(TICK1))
        
class MockTask(object):
    def __init__(self, *refiner_ports):
        self.refiner_ports = set(refiner_ports)