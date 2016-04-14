'''
Created on Oct 15, 2014

@author: stefan
'''
import unittest
import utils
from pydron.translation import deunbound

class TestFunctionalize(unittest.TestCase):

    def test_assignment(self):
        src = """
        def test():
            x = 1
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = 1
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
    
    def test_True(self):
        src = """
        def test():
            x = True
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = True
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
        
    def test_False(self):
        src = """
        def test():
            x = False
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = False
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
    def test_None(self):
        src = """
        def test():
            x = None
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = None
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
    def test_parameter(self):
        src = """
        def test(x):
            pass
        """
        expected = """
        def test(x):
            pass
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
        
    def test_use(self):
        src = """
        def test():
            x = 1
            print x
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = 1
            print __pydron_unbound_check__(x)
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
    def test_delete(self):
        src = """
        def test():
            x = 1
            del x
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = 1
            x = __pydron_unbound__
        """
        utils.compare(src, expected, deunbound.DeUnbound)
        
    def test_class(self):
        src = """
        class test(object):
            x = 1
        """
        expected = """
        class test(__pydron_unbound_check__(object)):
            x = __pydron_unbound__
            x = 1
        """
        utils.compare(src, expected, deunbound.DeUnbound)

    def test_builtin(self):
        src = """
        def test():
            __pydron_var__ = 1
            print __pydron_var__
        """
        expected = """
        def test():
            __pydron_var__ = 1
            print __pydron_var__
        """
        utils.compare(src, expected, deunbound.DeUnbound)

    def test_unchecked(self):
        src = """
        def test():
            x = 1
            print __pydron_unbound_unchecked__(x)
        """
        expected = """
        def test():
            x = __pydron_unbound__
            x = 1
            print __pydron_unbound_unchecked__(x)
        """
        utils.compare(src, expected, deunbound.DeUnbound)

