'''
Created on Oct 13, 2014

@author: stefan
'''
import unittest
import naming


class TestEncoding(unittest.TestCase):
    
    def testEncodeNoComp(self):
        self.assertEqual("foo", naming.encode_id("foo"))
        
    def testEncodeComp(self):
        self.assertEqual("foo$V1", naming.encode_id("foo", V=1))
        
    def testDecodeNoComp(self):
        self.assertEqual(("foo", dict()), naming.decode_id("foo"))
        
    def testDecodeComp(self):
        self.assertEqual(("foo", {"V":"1"}), naming.decode_id("foo$V1"))

        