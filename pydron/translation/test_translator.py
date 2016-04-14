# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.translation import translator, builtins
from pydron.dataflow import utils, tasks
from pydron.dataflow.graph import G, T, C, FINAL_TICK, START_TICK, graph_factory
import ast

class TestTranslator(unittest.TestCase):
    
    def test_FunctionDef(self):
        
        def f():
            return None


        expected = G(
            T(1, tasks.ConstTask(None), {'quick': True}),
            C(1, "value", FINAL_TICK, "retval")
        )
        
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_nested_FunctionDef(self):
        
        def f():
            def g():
                return None
            return g

        expected = G(
            T(1, tasks.FunctionDefTask("scheduler", 'g', [], None, None, 0, G(
                T(1, tasks.ConstTask(None), {'quick':True}),
                C(1, "value", FINAL_TICK, "retval")
            )), {'quick':True}),
            C(1, "function", FINAL_TICK, "retval")
        )
   
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_if(self):
        
        def f():
            t = True
            if t:
                x = 1
            else:
                x = 2
            return x

        expected = G(
            T(1, tasks.ConstTask(True), {'quick':True}),
            C(1, "value", 2, "$test"),
            T(2, tasks.IfTask(G(
                T(1, tasks.ConstTask(1), {'quick':True}),
                C(1, "value", FINAL_TICK, "x")
            ), G(
                T(1, tasks.ConstTask(2), {'quick':True}),
                C(1, "value", FINAL_TICK, "x")
            ))),
            C(2, "x", FINAL_TICK, "retval")
        )
   
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
        
    def test_if_half_assigned(self):
        
        def f():
            t = True
            x = 1
            if t:
                pass
            else:
                x = 2
            return x

        expected = G(
            T(1, tasks.ConstTask(True), {'quick':True}),
            T(2, tasks.ConstTask(1), {'quick':True}),
            C(1, "value", 3, "$test"),
            C(2, "value", 3, "x"),
            T(3, tasks.IfTask(G(
            ), G(
                T(1, tasks.ConstTask(2), {'quick':True}),
                C(1, "value", FINAL_TICK, "x")
            ))),
            C(3, "x", FINAL_TICK, "retval")
        )
   
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_if_inputs(self):
        
        def f():
            t = True
            c = 42
            if t:
                x = c
            else:
                x = c
            return x

        expected = G(
            T(1, tasks.ConstTask(True), {'quick':True}),
            T(2, tasks.ConstTask(42), {'quick':True}),
            C(1, "value", 3, "$test"),
            C(2, "value", 3, "c"),
            T(3, tasks.IfTask(G(
                C(START_TICK, "c", FINAL_TICK, "x")
            ), G(
                C(START_TICK, "c", FINAL_TICK, "x")
            ))),
            C(3, "x", FINAL_TICK, "retval")
        )
   
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_for(self):
        
        def f(lst, x):
            for x in lst:
                pass
            return x
            
        with graph_factory():
            expected = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask(), {'quick':True}),
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

        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_for_break(self):
        
        def f(lst, x):
            for x in lst:
                if True:
                    break
            return x
            
        with graph_factory():
            expected = G(
              C(START_TICK, "lst", 1, "iterable"),
              T(1, tasks.IterTask(), {'quick':True}),
              C(1, "value", 2, "$iterator"),
              C(START_TICK, "x", 2, "x"),
              T(2, tasks.ForTask(False, False, G("body",
                  T(1, tasks.ConstTask(True), {'quick':True}),
                  C(1, "value", 2, "$breaked"),
                  C(START_TICK, "$target",2 , "x"),
                  C(START_TICK, "$iterator", 2, "$iterator"),
                  T(2, tasks.ForTask(True, True, G("body"), G("else"))),
                  C(2, "x", FINAL_TICK, "x")
              ), G("else"))),
              C(2, "x", FINAL_TICK, "retval")
            )

        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_while(self):
        
        def f(x):
            while x:
                pass
            return x
            
        with graph_factory():
            expected = G(
              C(START_TICK, "x", 1, "$test"),
              C(START_TICK, "x", 1, "x"),
              T(1, tasks.WhileTask(False, False, G("body",
                  C(START_TICK, "x", 1 , "$test"),
                  C(START_TICK, "x", 1 , "x"),
                  T(1, tasks.WhileTask(True, False, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )

        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_while_break(self):
        
        def f(x):
            while x:
                if True:
                    break
            return x
            
        with graph_factory():
            expected = G(
              C(START_TICK, "x", 1, "$test"),
              C(START_TICK, "x", 1, "x"),
              T(1, tasks.WhileTask(False, False, G("body",
                  C(START_TICK, "x", 2 , "$test"),
                  C(START_TICK, "x", 2 , "x"),
                  T(1, tasks.ConstTask(True), {'quick':True}),
                  C(1, "value", 2, "$breaked"),
                  T(2, tasks.WhileTask(True, True, G("body"), G("else"))),
              ), G("else"))),
              C(START_TICK, "x", FINAL_TICK, "retval")
            )

        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_attribute_assign(self):
        
        def f(x, y):
            x.myattribute = y
            return x
            
        expected = G(
            C(START_TICK, "x", 1, "object"),
            C(START_TICK, "y", 1, "value"),
            T(1, tasks.AttrAssign("myattribute"), {'quick':True, 'syncpoint':True}),
            C(START_TICK, "x", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_subscript_assign(self):
        
        def f(x, y, z):
            x[y] = z
            return x
            
        expected = G(
            C(START_TICK, "x", 1, "object"),
            C(START_TICK, "y", 1, "slice"),
            C(START_TICK, "z", 1, "value"),
            T(1, tasks.SubscriptAssign(), {'quick':True, 'syncpoint':True}),
            C(START_TICK, "x", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_tuple_assign(self):
        
        def f(x):
            a, b, c = x
            return c
            
        expected = G(
            C(START_TICK, "x", 1, "value"),
            T(1, tasks.UnpackTask(3), {'quick':True}),
            C(1, "2", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_augassign(self):
        
        def f(a, b):
            a += b
            return a
            
        expected = G(
            C(START_TICK, "a", 1, "target"),
            C(START_TICK, "b", 1, "value"),
            T(1, tasks.AugAssignTask(ast.Add()), {'quick':True, 'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
        
    def test_augassign_attr(self):
        
        def f(a, b):
            a.myattr += b
            return a
            
        expected = G(
            C(START_TICK, "a", 1, "target"),
            C(START_TICK, "b", 1, "value"),
            T(1, tasks.AugAttrAssignTask(ast.Add(), "myattr"), {'quick':True, 'syncpoint':True}),
            C(START_TICK, "a", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_augassign_subscript(self):
        
        def f(a, b, i):
            a[i] += b
            return a
            
        expected = G(
            C(START_TICK, "a", 1, "target"),
            C(START_TICK, "b", 1, "value"),
            C(START_TICK, "i", 1, "slice"),
            T(1, tasks.AugSubscriptAssignTask(ast.Add()), {'quick':True, 'syncpoint':True}),
            C(START_TICK, "a", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_raise(self):
        
        def f(x):
            raise x
            return x
        
        expected = G(
            T(1, tasks.ConstTask(None), {'quick':True}),
            C(1, "value", 2, "inst"),
            C(START_TICK, "x", 2, "type"),
            C(1, "value", 2, "tback"),
            T(2, tasks.RaiseTask(), {'quick':True}),
            C(START_TICK, "x", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_binop(self):
        
        def f(a, b):
            return a + b
        
        expected = G(
            C(START_TICK, "a", 1, "left"),
            C(START_TICK, "b", 1, "right"),
            T(1, tasks.BinOpTask(ast.Add()), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_unaryop(self):
        
        def f(a):
            return ~a
        
        expected = G(
            C(START_TICK, "a", 1, "value"),
            T(1, tasks.UnaryOpTask(ast.Invert()), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_dict(self):
        
        def f(k1, v1, k2, v2):
            return {k1:v1, k2:v2}
        
        expected = G(
            C(START_TICK, "k1", 1, "key_0"),
            C(START_TICK, "v1", 1, "value_0"),
            C(START_TICK, "k2", 1, "key_1"),
            C(START_TICK, "v2", 1, "value_1"),
            T(1, tasks.DictTask(2), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_set(self):
        
        def f(v1, v2):
            return {v1, v2}
        
        expected = G(
            C(START_TICK, "v1", 1, "value_0"),
            C(START_TICK, "v2", 1, "value_1"),
            T(1, tasks.SetTask(2), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_compare(self):
        
        def f(a, b):
            return a == b
        
        expected = G(
            C(START_TICK, "a", 1, "left"),
            C(START_TICK, "b", 1, "right"),
            T(1, tasks.BinOpTask(ast.Eq()), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_call(self):
        
        def f(a):
            return a()
        
        expected = G(
            C(START_TICK, "a", 1, "func"),
            T(1, tasks.CallTask(0, [], False, False), {'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_call_args(self):
        
        def f(a,b,c,d):
            return a(b,c,d)
        
        expected = G(
            C(START_TICK, "a", 1, "func"),
            C(START_TICK, "b", 1, "arg_0"),
            C(START_TICK, "c", 1, "arg_1"),
            C(START_TICK, "d", 1, "arg_2"),
            T(1, tasks.CallTask(3, [], False, False), {'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_call_karg(self):
        
        def f(a,b,c):
            return a(foo=b, bar=c)
        
        expected = G(
            C(START_TICK, "a", 1, "func"),
            C(START_TICK, "b", 1, "karg_0"),
            C(START_TICK, "c", 1, "karg_1"),
            T(1, tasks.CallTask(0, ['foo', 'bar'], False, False), {'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_call_starargs(self):
        
        def f(a,b):
            return a(*b)
        
        expected = G(
            C(START_TICK, "a", 1, "func"),
            C(START_TICK, "b", 1, "starargs"),
            T(1, tasks.CallTask(0, [], True, False), {'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    
    def test_call_builtin(self):
        def f():
            return __pydron_new_cell__("x") #@UndefinedVariable
        
        expected = G(
            T(1, tasks.ConstTask("x"), {'quick': True}),
            C(1, "value", 2, "arg0"),
            T(2, tasks.BuiltinCallTask(builtins.__pydron_new_cell__, 1), {'quick': True}),
            C(2, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_call_kwargs(self):
        
        def f(a,b):
            return a(**b)
        
        expected = G(
            C(START_TICK, "a", 1, "func"),
            C(START_TICK, "b", 1, "kwargs"),
            T(1, tasks.CallTask(0, [], False, True), {'syncpoint':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_num(self):
        
        def f():
            return 42
        
        expected = G(
            T(1, tasks.ConstTask(42), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_str(self):
        
        def f():
            return "Hello World!"
        
        expected = G(
            T(1, tasks.ConstTask("Hello World!"), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
        
    def test_attribute(self):
        
        def f(a):
            return a.myattr
        
        expected = G(
            C(START_TICK, "a", 1, "object"),
            T(1, tasks.AttributeTask("myattr"), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_slice(self):
        
        def f(a,b):
            return a[b]
        
        expected = G(
            C(START_TICK, "a", 1, "object"),
            C(START_TICK, "b", 1, "slice"),
            T(1, tasks.SubscriptTask(), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
        
    def test_list(self):
        
        def f(v1, v2):
            return [v1, v2]
        
        expected = G(
            C(START_TICK, "v1", 1, "value_0"),
            C(START_TICK, "v2", 1, "value_1"),
            T(1, tasks.ListTask(2), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_tuple(self):
        
        def f(v1, v2):
            return (v1, v2)
        
        expected = G(
            C(START_TICK, "v1", 1, "value_0"),
            C(START_TICK, "v2", 1, "value_1"),
            T(1, tasks.TupleTask(2), {'quick':True}),
            C(1, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        
    def test_readglobal(self):
    
        def f():
            return __pydron_read_global__("TestTranslator")  #@UndefinedVariable
        
        expected = G(
            T(1, tasks.ConstTask("TestTranslator"), {'quick':True}),
            C(1, "value", 2, "var"),
            T(2, tasks.ReadGlobal(__name__), {'quick': True}),
            C(2, "value", FINAL_TICK, "retval")      
        )
        
        callee = translator.translate_function(f, "scheduler", False)
        utils.assert_graph_equal(expected, callee.graph)
        