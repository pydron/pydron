# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, delocals


class DeLocals(unittest.TestCase):

    def test_func_local(self):
        src = """
        def test():
            x = 1
            locals()
        """
        expected = """
        def test():
            x = 1
            __pydron_locals__({'x': __pydron_unbound_unchecked__(x)})
        """
        utils.compare(src, expected, delocals.DeLocals)
        
    def test_func_free(self):
        src = """
        def test():
            x = 1
            def inner(x):
                print x
                locals()
        """
        expected = """
        def test():
            x = 1
            def inner(x):
                print x
                __pydron_locals__({'x': __pydron_unbound_unchecked__(x)})
        """
        utils.compare(src, expected, delocals.DeLocals)

    def test_func_free_passthrough(self):
        src = """
        def test():
            x = 1
            def middle():
                def inner():
                    print x
                locals()
        """
        expected = """
        def test():
            x = 1
            def middle():
                def inner():
                    print x
                __pydron_locals__({'x':__pydron_unbound_unchecked__(x), 
                        'inner':__pydron_unbound_unchecked__(inner)})
        """
        utils.compare(src, expected, delocals.DeLocals)

    def test_class(self):
        src = """
        class Test(object):
            def foo(self):
                pass
            locals()
        """
        expected = """
        class Test(object):
            def foo(self):
                pass
            __pydron_locals__({'foo':__pydron_unbound_unchecked__(foo)})
        """
        utils.compare(src, expected, delocals.DeLocals)

    def test_class_free(self):
        src = """
        def test():
            x = 1
            class Test(object):
                y = 1
                print x
                locals()
        """
        expected = """
        def test():
            x = 1
            class Test(object):
                y = 1
                print x
                __pydron_locals__({'y':__pydron_unbound_unchecked__(y)})
        """
        utils.compare(src, expected, delocals.DeLocals)


        