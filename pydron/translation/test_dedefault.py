# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, dedefault

class TestDeDefault(unittest.TestCase):

    def test_noargs(self):
        src = """
        def test():
            pass
        """
        expected = """
        def test():
            pass
        """
        utils.compare(src, expected, dedefault.DeDefault)

    def test_nodefaults(self):
        src = """
        def test(a,b,c):
            pass
        """
        expected = """
        def test(a,b,c):
            pass
        """
        utils.compare(src, expected, dedefault.DeDefault)

    def test_default(self):
        src = """
        def test(a,b,c=3):
            pass
        """
        expected = """
        def test__U0(a,b,c):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (3,)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)
        
    def test_default_expr(self):
        src = """
        def test(a,b,c=x*y):
            pass
        """
        expected = """
        def test__U0(a,b,c):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (x*y,)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)

    def test_defaults(self):
        src = """
        def test(a,b=2,c=3):
            pass
        """
        expected = """
        def test__U0(a,b,c):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (2, 3)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)
        
    def test_alldefaults(self):
        src = """
        def test(a=1,b=2,c=3):
            pass
        """
        expected = """
        def test__U0(a,b,c):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (1,2,3)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)

    def test_args(self):
        src = """
        def test(a,b,c=3, *args):
            pass
        """
        expected = """
        def test__U0(a,b,c,*args):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (3,)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)
        
    def test_kwargs(self):
        src = """
        def test(a,b,c=3, **kwargs):
            pass
        """
        expected = """
        def test__U0(a,b,c,**kwargs):
            pass
        tuple__U0 = ('a', 'b', 'c')
        tuple__U1 = (3,)
        test = __pydron_defaults__(test__U0,  tuple__U0, tuple__U1)
        """
        utils.compare(src, expected, dedefault.DeDefault)

