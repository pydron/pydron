# Copyright (C) 2015 Stefan C. Mueller

import unittest
import datetime
import pickle
import pydron.picklesupport

class Dummy(object):
    def __init__(self):
        self.value = 1
    def f(self):
        return 42 + self.value

class TestPickleSupport(unittest.TestCase):
    
    def test_module(self):
        dump = pickle.dumps(unittest, pickle.HIGHEST_PROTOCOL)
        load = pickle.loads(dump)
        self.assertIs(load, unittest)
    
    def test_builtin_function(self):
        dump = pickle.dumps(map, pickle.HIGHEST_PROTOCOL)
        load = pickle.loads(dump)
        self.assertIs(load, map)
    
    def test_builtin_method(self):
        delta = datetime.timedelta(seconds=10)
        func = delta.total_seconds
        dump = pickle.dumps(func, pickle.HIGHEST_PROTOCOL)
        load = pickle.loads(dump)
        self.assertEqual(10, load())

    def test_method(self):
        x = Dummy()
        dump = pickle.dumps(x.f, pickle.HIGHEST_PROTOCOL)
        load = pickle.loads(dump)
        self.assertEqual(43, load())