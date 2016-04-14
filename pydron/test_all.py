# Copyright (C) 2015 Stefan C. Mueller

import unittest
import utwist
import pydron
import logging
from twisted.internet import threads

logging.basicConfig(level=logging.DEBUG)


def run_in_thread(func):
    def wrapper(*args, **kwargs):
        return threads.deferToThread(func, *args, **kwargs)
    return wrapper


class IntegrationTests(unittest.TestCase):
    
    @utwist.with_reactor
    @run_in_thread
    def test_default_return_value(self):
        @pydron.schedule
        def target():
            pass
        self.assertIsNone(target())
        
        
    @utwist.with_reactor
    @run_in_thread
    def test_return_value(self):
        @pydron.schedule
        def target():
            return 42
        self.assertEqual(42, target())
        
    @utwist.with_reactor
    @run_in_thread
    def test_binop(self):
        @pydron.schedule
        def target():
            return 40 + 2
        self.assertEqual(42, target())
        
    @utwist.with_reactor
    @run_in_thread
    def test_unaryop(self):
        @pydron.schedule
        def target():
            return -42
        self.assertEqual(-42, target())
        
    @utwist.with_reactor
    @run_in_thread
    def test_tuple(self):
        @pydron.schedule
        def target():
            return (1,2)
        self.assertEqual((1,2), target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_list(self):
        @pydron.schedule
        def target():
            return [1,2]
        self.assertEqual([1,2], target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_set(self):
        @pydron.schedule
        def target():
            return {1,2}
        self.assertEqual({1,2}, target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_dict(self):
        @pydron.schedule
        def target():
            return {1:2}
        self.assertEqual({1:2}, target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_subscript(self):
        @pydron.schedule
        def target():
            return [0,1,2][1]
        self.assertEqual(1, target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_if_true(self):
        @pydron.schedule
        def target():
            if 1+2 == 3:
                return "a"
            else:
                return "b"
        self.assertEqual("a", target())
        
    @utwist.with_reactor
    @run_in_thread
    def test_if_false(self):
        @pydron.schedule
        def target():
            if 1+2 == 4:
                return "a"
            else:
                return "b"
        self.assertEqual("b", target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_arg(self):
        @pydron.schedule
        def target(x):
            return x
        self.assertEqual(42, target(42)) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_args(self):
        @pydron.schedule
        def target(*args):
            return args[0]
        self.assertEqual(42, target(42)) 
        
        
    @utwist.with_reactor
    @run_in_thread
    def test_call(self):
        @pydron.schedule
        def target():
            return mock_function(1,2,3)
        self.assertEqual(((1,2,3), {}), target()) 
        
        
    @utwist.with_reactor
    @run_in_thread
    def test_call_args(self):
        @pydron.schedule
        def target():
            return mock_function(*(1,2,3))
        self.assertEqual(((1,2,3), {}), target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_call_kwargs(self):
        @pydron.schedule
        def target():
            return mock_function(a=1, b=2)
        self.assertEqual((tuple(), {"a":1, "b":2}), target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_while(self):
        @pydron.schedule
        def target():
            i = 3
            out = []
            while i > 0:
                out += [i**2]
                i-=1
            return out
        self.assertEqual([9,4,1], target()) 
        
        
    @utwist.with_reactor
    @run_in_thread
    def test_for(self):
        @pydron.schedule
        def target():
            out = []
            for x in [1,2,3]:
                out += [x**2]
            return out
        self.assertEqual([1,4,9], target()) 
        
    @utwist.with_reactor
    @run_in_thread
    def test_attr_assign(self):
        @pydron.schedule
        def target():
            x = MockClass()
            x.abc = "Hello"
            return x.abc
        self.assertEqual("Hello", target()) 
        
def mock_function(*args, **kwargs):
    return args, kwargs

class MockClass(object):
    pass