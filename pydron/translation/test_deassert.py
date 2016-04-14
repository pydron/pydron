# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, deassert

class TestDeAssert(unittest.TestCase):

        
    def test_assert(self):
        src = """
        def test():
            assert abc
        """
        expected = """
        def test():
            if __debug__:
                if not abc:
                    raise AssertionError
        """
        utils.compare(src, expected, deassert.DeAssert)
        
    def test_assert_msg(self):
        src = """
        def test():
            assert abc, "hello"
        """
        expected = """
        def test():
            if __debug__:
                if not abc:
                    raise AssertionError("hello")
        """
        utils.compare(src, expected, deassert.DeAssert)


        