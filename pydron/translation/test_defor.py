# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.translation import utils, defor


class TestDeFor(unittest.TestCase):

    def test_simple(self):
        src = """
        for x in [1,2,3]:
            print x
        """
        expected = """
        iterator__U0 = __pydron_iter__([1,2,3])
        while __pydron_hasnext__(iterator__U0):
            x, iterator__U0 = __pydron_next__(iterator__U0)
            print x
        """
        utils.compare(src, expected, defor.DeFor)
        
    def test_nested(self):
        src = """
        for x in [1,2,3]:
            for y in [4,5,6]:
                print x
        """
        expected = """
        iterator__U1 = __pydron_iter__([1,2,3])
        while __pydron_hasnext__(iterator__U1):
            x, iterator__U1 = __pydron_next__(iterator__U1)
            iterator__U0 = __pydron_iter__([4,5,6])
            while __pydron_hasnext__(iterator__U0):
                y, iterator__U0 = __pydron_next__(iterator__U0)
                print x
        """
        utils.compare(src, expected, defor.DeFor)

    def test_orelse(self):
        src = """
        for x in [1,2,3]:
            print x
        else:
            print "hello"
        """
        expected = """
        iterator__U0 = __pydron_iter__([1,2,3])
        while __pydron_hasnext__(iterator__U0):
            x, iterator__U0 = __pydron_next__(iterator__U0)
            print x
        else:
            print "hello"
        """
        utils.compare(src, expected, defor.DeFor)
