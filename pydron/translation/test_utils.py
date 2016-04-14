'''
Created on Oct 13, 2014

@author: stefan
'''
import unittest
import utils

class TestUnindent(unittest.TestCase):

    def testEmptyString(self):
        self.assertEqual("", utils.unindent(""))
        
    def testOneLineNoIndent(self):
        self.assertEqual("x=1", utils.unindent("x=1"))
        
    def testOneLineSpaces(self):
        self.assertEqual("x=1", utils.unindent("  x=1"))
        
    def testOneLineTabs(self):
        self.assertEqual("x=1", utils.unindent("\t\tx=1"))
        
    def testOneLineMix(self):
        self.assertEqual("x=1", utils.unindent(" \t \t  x=1"))
        
    def testTwoLines(self):
        self.assertEqual("x=1\ny=2", utils.unindent("x=1\ny=2"))
        
    def testTwoLinesSpaces(self):
        self.assertEqual("x=1\ny=2", utils.unindent("  x=1\n  y=2"))
        
    def testTwoLinesTabs(self):
        self.assertEqual("x=1\ny=2", utils.unindent("\tx=1\n\ty=2"))
        
    def testTwoLinesMixed(self):
        self.assertEqual("x=1\ny=2", utils.unindent("\tx=1\n        y=2"))

    def testStructurePreserved(self):
        self.assertEqual("def foo():\n  x=1", utils.unindent("def foo():\n  x=1"))
        
    def testStructurePreservedSpaces(self):
        self.assertEqual("def foo():\n  x=1", utils.unindent("  def foo():\n    x=1"))

    def testStructurePreservedTabs(self):
        self.assertEqual("def foo():\n  x=1", utils.unindent("\tdef foo():\n\t  x=1"))
        
    def testIgnoreEmtptyLines(self):
        self.assertEqual("\nx=1", utils.unindent("\n   x=1"))
        
    def testIgnoreComments(self):
        self.assertEqual("#comment\nx=1", utils.unindent("#comment\n   x=1"))
        
    def testPartiallyIndendedComment(self):
        self.assertEqual("#comment\nx=1", utils.unindent(" #comment\n   x=1"))
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
