'''
Created on Oct 15, 2014

@author: stefan
'''
import unittest
import utils
from pydron.translation import deimport

class TestDeImport(unittest.TestCase):


    def testModImport(self):
        src = """
        import x
        """
        expected = """
        x = __import__('x', globals(), None, None)
        """
        utils.compare(src, expected, deimport.DeImport)

    def testFuncImport(self):
        src = """
        def test():
            import x
        """
        expected = """
        def test():
            x = __import__('x', globals(), None, None)
        """
        utils.compare(src, expected, deimport.DeImport)

    def testImportMultiple(self):
        src = """
        import x, y
        """
        expected = """
        x = __import__('x', globals(), None, None)
        y = __import__('y', globals(), None, None)
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportNested(self):
        src = """
        import x.y
        """
        expected = """
        x = __import__('x.y', globals(), None, None)
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportAlias(self):
        src = """
        import x as y
        """
        expected = """
        y = __import__('x', globals(), None, None)
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFrom(self):
        src = """
        from x import y
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('y',))
        y = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromMultiple(self):
        src = """
        from x import y, z
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('y', 'z'))
        y = module__U0.y
        z = module__U0.z
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromAs(self):
        src = """
        from x import y as z
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('y',))
        z = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromNested(self):
        src = """
        from a.b.c import y
        """
        expected = """
        module__U0 = __import__('a.b.c', globals(), None, ('y',))
        y = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromRelative1(self):
        src = """
        from .x import y
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('y',), 1)
        y = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromRelative2(self):
        src = """
        from ..x import y
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('y',), 2)
        y = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromPureRelative(self):
        src = """
        from . import y
        """
        expected = """
        module__U0 = __import__(None, globals(), None, ('y',), 1)
        y = module__U0.y
        """
        utils.compare(src, expected, deimport.DeImport)
        
    def testImportFromStar(self):
        src = """
        from x import *
        """
        expected = """
        module__U0 = __import__('x', globals(), None, ('*',))
        for module_element__U0 in getattr(module__U0, '__all__', dir(module__U0)):
            globals()[module_element__U0] = getattr(module__U0, module_element__U0)
        """
        utils.compare(src, expected, deimport.DeImport)