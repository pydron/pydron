# Copyright (C) 2014 Stefan C. Mueller

import unittest
import naming
from pydron.translation import utils, dedecorator
import astor
import ast
import itertools

class TestDeDecorator(unittest.TestCase):

    def test_func_nodecorator(self):
        src = """
        def test():
            pass
        """
        expected = """
        def test():
            pass
        """
        utils.compare(src, expected, dedecorator.DeDecorator)
        
    def test_func_one(self):
        src = """
        @mydecorator
        def test():
            pass
        """
        expected = """
        def test__U0():
            pass
        test = mydecorator(test__U0)
        """
        utils.compare(src, expected, dedecorator.DeDecorator)
        
    def test_func_two(self):
        src = """
        @mydecorator1
        @mydecorator2
        def test():
            pass
        """
        expected = """
        def test__U0():
            pass
        test = mydecorator1(mydecorator2(test__U0))
        """
        utils.compare(src, expected, dedecorator.DeDecorator)

    def test_func_arguments(self):
        src = """
        @mydecorator(1,2,3)
        def test():
            pass
        """
        expected = """
        def test__U0():
            pass
        test = mydecorator(1,2,3)(test__U0)
        """
        utils.compare(src, expected, dedecorator.DeDecorator)

    def test_func_two_args(self):
        src = """
        @mydecorator1(1)
        @mydecorator2(2)
        def test():
            pass
        """
        expected = """
        def test__U0():
            pass
        test = mydecorator1(1)(mydecorator2(2)(test__U0))
        """
        utils.compare(src, expected, dedecorator.DeDecorator)

    def test_class_none(self):
        src = """
        class test:
            pass
        """
        expected = """
        class test:
            pass
        """
        utils.compare(src, expected, dedecorator.DeDecorator)


    def test_class_one(self):
        src = """
        @mydecorator
        class test:
            pass
        """
        expected = """
        class test__U0():
            pass
        test = mydecorator(test__U0)
        """
        utils.compare(src, expected, dedecorator.DeDecorator)
        