'''
Created on Oct 15, 2014

@author: stefan
'''
import unittest
import utils
from pydron.translation import deglobal

class TestLocalizeGlobalVariables(unittest.TestCase):


    def test_read_implicit(self):
        src = """
        def test():
            print x
        """
        expected = """
        def test():
            print __pydron_read_global__('x')
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_read_explicit(self):
        src = """
        def test():
            global x
            print x
        """
        expected = """
        def test():
            print __pydron_read_global__('x')
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_assign_explicit(self):
        src = """
        def test():
            global x
            x = 1
        """
        expected = """
        def test():
            __pydron_assign_global__('x', 1)
        """
        utils.compare(src, expected, deglobal.DeGlobal)

    def test_assign_mixed(self):
        src = """
        def test():
            global x
            x = 1
            print x
        """
        expected = """
        def test():
            __pydron_assign_global__('x', 1)
            print __pydron_read_global__('x')
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_builtin(self):
        src = """
        def test():
            globals()
        """
        expected = """
        def test():
            __pydron_read_global__('globals')()
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        

    def test_FunctionDef(self):
        src = """
        def test():
            global x
            def x():
                pass
        """
        expected = """
        def test():
            def x__U0():
                pass
            __pydron_assign_global__('x', x__U0)
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_ClassDef(self):
        src = """
        def test():
            global x
            class x():
                pass
        """
        expected = """
        def test():
            class x__U0():
                pass
            __pydron_assign_global__('x', x__U0)
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_TryExcept(self):
        src = """
        def test():
            global e
            try:
                pass
            except ValueException as e:
                pass
        """
        expected = """
        def test():
            try:
                pass
            except __pydron_read_global__('ValueException') as e:
                __pydron_assign_global__('e', e)
                pass
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_None(self):
        src = """
        def test():
            return None
        """
        expected = """
        def test():
            return None
        """
        utils.compare(src, expected, deglobal.DeGlobal)

        
    def test_True(self):
        src = """
        def test():
            return None
        """
        expected = """
        def test():
            return None
        """
        utils.compare(src, expected, deglobal.DeGlobal)


    def test_False(self):
        src = """
        def test():
            return None
        """
        expected = """
        def test():
            return None
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_delete(self):
        src = """
        def test():
            global x
            del x
        """
        expected = """
        def test():
            __pydron_delete_global__('x')
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_delete_multiple(self):
        src = """
        def test():
            global x, y
            del x, y
        """
        expected = """
        def test():
            __pydron_delete_global__('x')
            __pydron_delete_global__('y')
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_delete_non_global(self):
        src = """
        def test():
            del x, y
        """
        expected = """
        def test():
            del x
            del y
        """
        utils.compare(src, expected, deglobal.DeGlobal)
        
    def test_delete_mix(self):
        src = """
        def test():
            global y
            del x, y, z
        """
        expected = """
        def test():
            del x
            __pydron_delete_global__('y')
            del z
        """
        utils.compare(src, expected, deglobal.DeGlobal)