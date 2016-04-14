'''
Created on Oct 21, 2014

@author: stefan
'''
import unittest
import utils
from pydron.translation import declass


class Test(unittest.TestCase):


    def test_class(self):
        src = """
        def test():
            class X(object):
                a = 1
                def foo():
                    pass
                __pydron_members__ = 123
                    
        """
        expected = """
        def test():
            def class_X__U0():
                a = 1
                def foo():
                    pass
                __pydron_members__ = 123
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0())
        """
        utils.compare(src, expected, declass.DeClass)
        
    def test_subclass(self):
        src = """
        def test():
            class X(object):
                class Y(object):
                    __pydron_members__ = 123
                __pydron_members__ = 456
        """
        expected = """
        def test():
            def class_X__U0():
                def class_Y__U0():
                    __pydron_members__ = 123
                    return __pydron_members__
                Y = __pydron_read_global__('type')('Y', (object,), class_Y__U0())
                __pydron_members__ = 456
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0())
        """
        utils.compare(src, expected, declass.DeClass)
        
    def test_free(self):
        src = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            class X(object):
                a = x.cell_contents
                __pydron_members__ = 123
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            def class_X__U0(x):
                a = x.cell_contents
                __pydron_members__ = 123
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0(x))
        """
        utils.compare(src, expected, declass.DeClass)
        
    def test_passthrough(self):
        src = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            class X(object):
                def foo__U0(x, self):
                      print x.cell_contents
                foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                __pydron_members__ = 123
                    
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            def class_X__U0(x__P1):
                def foo__U0(x, self):
                      print x.cell_contents
                foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                __pydron_members__ = 123
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0(x))
        """
        utils.compare(src, expected, declass.DeClass)
        
    def test_passthrough_overwrite(self):
        src = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            class X(object):
                x = 'hides free var'
                def foo__U0(x, self):
                      print x.cell_contents
                foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                __pydron_members__ = 123
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            def class_X__U0(x__P1):
                x = 'hides free var'
                def foo__U0(x, self):
                      print x.cell_contents
                foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                __pydron_members__ = 123
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0(x))
        """
        utils.compare(src, expected, declass.DeClass)
        
    def test_passthrough_nested(self):
        src = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            class X(object):
                x = 'hides free var'
                class Y(object):
                    x = 'hides free var too'
                    def foo__U0(x, self):
                          print x.cell_contents
                    foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                    __pydron_members__ = 123
                __pydron_members__ = 123
        """
        expected = """
        def test():
            x = __pydron_new_cell__('x')
            x.cell_contents = 42
            def class_X__U0(x__P1):
                x = 'hides free var'
                
                def class_Y__U0(x__P1):
                    x = 'hides free var too'
                    def foo__U0(x, self):
                          print x.cell_contents
                    foo = __pydron_wrap_closure__(foo__U0, (x__P1,))
                    __pydron_members__ = 123
                    return __pydron_members__
                Y = __pydron_read_global__('type')('Y', (object,), class_Y__U0(x__P1))
                
                __pydron_members__ = 123
                return __pydron_members__
            X = __pydron_read_global__('type')('X', (object,), class_X__U0(x))
        """
        utils.compare(src, expected, declass.DeClass)
        
