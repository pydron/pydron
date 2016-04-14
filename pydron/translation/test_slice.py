# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.translation import utils, deslice


class TestDeSlice(unittest.TestCase):
    
    def test_index(self):
        src = """
        def test():
            obj[1]
        """
        expected = """
        def test():
            obj[1]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
        
    def test_slice(self):
        src = """
        def test():
            obj[1:2]
        """
        expected = """
        def test():
            obj[slice(1,2,None)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_slice_step(self):
        src = """
        def test():
            obj[1:2:3]
        """
        expected = """
        def test():
            obj[slice(1,2,3)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_slice_left(self):
        src = """
        def test():
            obj[:1]
        """
        expected = """
        def test():
            obj[slice(None,1,None)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_slice_right(self):
        src = """
        def test():
            obj[1:]
        """
        expected = """
        def test():
            obj[slice(1,None,None)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_slice_left_step(self):
        src = """
        def test():
            obj[:1:2]
        """
        expected = """
        def test():
            obj[slice(None,1,2)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_slice_right_step(self):
        src = """
        def test():
            obj[1::2]
        """
        expected = """
        def test():
            obj[slice(1,None,2)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
    def test_extslice(self):
        src = """
        def test():
            obj[1,2,3]
        """
        expected = """
        def test():
            obj[(1,2,3)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
        
    def test_extslice_slice(self):
        src = """
        def test():
            obj[1,2:3,4]
        """
        expected = """
        def test():
            obj[(1,slice(2,3,None),4)]
        """
        utils.compare(src, expected, deslice.DeSlice)
        
        
        