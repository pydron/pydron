# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, demultitarget


class TestDeMultiTarget(unittest.TestCase):

    def test_single_assignment(self):
        src = """
        x = 1
        """
        expected = """
        x = 1
        """
        utils.compare(src, expected, demultitarget.DeMultiTarget)

    def test_multi_assignment_name(self):
        src = """
        x = y = a
        """
        expected = """
        x = a
        y = a
        """
        utils.compare(src, expected, demultitarget.DeMultiTarget)
        
    def test_multi_assignment_str(self):
        src = """
        x = y = "a"
        """
        expected = """
        x = "a"
        y = "a"
        """
        utils.compare(src, expected, demultitarget.DeMultiTarget)
        
    def test_multi_assignment_num(self):
        src = """
        x = y = 1
        """
        expected = """
        x = 1
        y = 1
        """
        utils.compare(src, expected, demultitarget.DeMultiTarget)
        
    def test_multi_assignment_complex(self):
        src = """
        x = y = 1 + 2
        """
        expected = """
        value__U0 = 1 + 2
        x = value__U0
        y = value__U0
        """
        utils.compare(src, expected, demultitarget.DeMultiTarget)