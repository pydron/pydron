# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, deprint

class TestDePrint(unittest.TestCase):


    def test_single_obj(self):
        src = """
        def test():
            print "Hello"
        """
        expected = """
        def test():
            __pydron_print__(None, ("Hello",), True)
        """
        utils.compare(src, expected, deprint.DePrint)

    def test_multiple_obj(self):
        src = """
        def test():
            print "Hello", "World"
        """
        expected = """
        def test():
            __pydron_print__(None, ("Hello", "World"), True)
        """
        utils.compare(src, expected, deprint.DePrint)
        
    def test_nonewline(self):
        src = """
        def test():
            print "Hello", 
        """
        expected = """
        def test():
            __pydron_print__(None, ("Hello",), False)
        """
        utils.compare(src, expected, deprint.DePrint)
        
    def test_stream(self):
        src = """
        def test():
            print >> stream, "Hello" 
        """
        expected = """
        def test():
            __pydron_print__(stream, ("Hello",), True)
        """
        utils.compare(src, expected, deprint.DePrint)
        
    def test_stream_multiple(self):
        src = """
        def test():
            print >> stream, "Hello", "World"
        """
        expected = """
        def test():
            __pydron_print__(stream, ("Hello", "World"), True)
        """
        utils.compare(src, expected, deprint.DePrint)
        
    def test_stream_nonewline(self):
        src = """
        def test():
            print >> stream, "Hello", 
        """
        expected = """
        def test():
            __pydron_print__(stream, ("Hello",), False)
        """
        utils.compare(src, expected, deprint.DePrint)
        
        