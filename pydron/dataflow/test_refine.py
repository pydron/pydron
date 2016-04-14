# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.dataflow import refine, utils
from pydron.dataflow.graph import G,T,C, START_TICK, FINAL_TICK

class TestReplaceTask(unittest.TestCase):
    
    def test_in_out(self):
        
        subgraph = G(
            C(START_TICK, "sin", 1, "x"),
            T(1, "subtask"),
            C(1, "y", FINAL_TICK, "sout")
        )
        
        g = G(
              C(START_TICK, "in", 1, "sin"),
              T(1, "task_to_replace"),
              C(1, "sout", FINAL_TICK, "out")
              )
        
        expected  = G(
              C(START_TICK, "in", (1,1), "x"),
              T((1,1), "subtask"),
              C((1,1), "y", FINAL_TICK, "out")
              )
        
        refine.replace_task(g, START_TICK + 1, subgraph)
        
        utils.assert_graph_equal(expected, g)
        
    def test_unassigned_out(self):
        
        subgraph = G(
            C(START_TICK, "sin", 1, "x"),
            T(1, "subtask"),
            C(1, "y", FINAL_TICK, "sout")
        )
        
        g = G(
              C(START_TICK, "in", 1, "sin"),
              C(START_TICK, "sout2", 1, "sout2"),
              T(1, "task_to_replace"),
              C(1, "sout", FINAL_TICK, "out"),
              C(1, "sout2", FINAL_TICK, "out2")
              )
        
        expected  = G(
              C(START_TICK, "in", (1,1), "x"),
              T((1,1), "subtask"),
              C((1,1), "y", FINAL_TICK, "out"),
              C(START_TICK, "sout2", FINAL_TICK, "out2")
              )
        
        refine.replace_task(g, START_TICK + 1, subgraph)
        
        utils.assert_graph_equal(expected, g)
        
        
    def test_passhtrough(self):
        
        subgraph = G(
            C(START_TICK, "sin", FINAL_TICK,"sout"),
        )
        
        g = G(
              C(START_TICK, "in", 1, "sin"),
              T(1, "task_to_replace"),
              C(1, "sout", FINAL_TICK, "out"),
              )
        
        expected  = G(
              C(START_TICK, "in", FINAL_TICK, "out"),
              )
        
        refine.replace_task(g, START_TICK + 1, subgraph)
        
        utils.assert_graph_equal(expected, g)
        