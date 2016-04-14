'''
Created on Oct 15, 2014

@author: stefan
'''
import unittest
import utils
from pydron.translation import defree

        
class TestDeFree(unittest.TestCase):

    def test_closure(self):
        src = """
        def test():
            x = 1
            def inner():
                print x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 1
            def inner__U0(x):
                print x.cell_contents
            inner = __pydron_wrap_closure__(inner__U0, (x,))
        """
        utils.compare(src, expected, defree.DeFree)
        

    def test_shared_parameter(self):
        src = """
        def test(x):
            def inner():
                print x
        """
        expected = """
        def test(x):
            x__U0 = x
            x = __pydron_new_cell__('x')
            x.cell_contents = x__U0
            def inner__U0(x):
                print x.cell_contents
            inner = __pydron_wrap_closure__(inner__U0, (x,))
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_passthrough(self):
        src = """
        def test():
            x = 1
            def middle():
                def inner():
                    print x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 1
            def middle__U0(x):
                def inner__U0(x):
                    print x.cell_contents
                inner = __pydron_wrap_closure__(inner__U0, (x,))
            middle = __pydron_wrap_closure__(middle__U0, (x,))
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_nested(self):
        src = """
        def test():
            x = 1
            def middle():
                print x
                def inner():
                    print x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 1
            def middle__U0(x):
                print x.cell_contents
                def inner__U0(x):
                    print x.cell_contents
                inner = __pydron_wrap_closure__(inner__U0, (x,))
            middle = __pydron_wrap_closure__(middle__U0, (x,))
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_class(self):
        src = """
        def test():
            x = 1
            class X(object):
                print x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 1
            class X(object):
                print x.cell_contents
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_class_notfree(self):
        src = """
        def test():
            x = 1
            class X(object):
                x = 2
        """
        expected = """
        def test():
            x = 1
            class X(object):
                x = 2
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_class_passthrough(self):
        src = """
        def test():
            x = 1
            class X(object):
                def foo():
                    print x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 1
            class X(object):
                def foo__U0(x):
                    print x.cell_contents
                foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
        """
        utils.compare(src, expected, defree.DeFree)
        
    def test_class_free(self):
        src = """
        def test():
            x = 42
            class X(object):
                a = x
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            class X(object):
                a = x.cell_contents
        """
        utils.compare(src, expected, defree.DeFree)