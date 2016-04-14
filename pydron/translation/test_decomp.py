# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, decomp

class TestDeComp(unittest.TestCase):

    def test_list(self):
        src = """
        def test():
            return [x for x in lst]
        """
        expected = """
        def test():
            return [x for x in lst]
        """
        utils.compare(src, expected, decomp.DeComp)
        
    def test_set(self):
        src = """
        def test():
            return {x for x in lst}
        """
        expected = """
        def test():
            return set([x for x in lst])
        """
        utils.compare(src, expected, decomp.DeComp)

    def test_dict(self):
        src = """
        def test():
            return {k:v for k,v in lst}
        """
        expected = """
        def test():
            return dict([(k,v) for k,v in lst])
        """
        utils.compare(src, expected, decomp.DeComp)

    def test_set_nested_list(self):
        src = """
        def test():
            return {x for x in {y for y in lst}}
        """
        expected = """
        def test():
            return set([x for x in set([y for y in lst])])
        """
        utils.compare(src, expected, decomp.DeComp)

    def test_set_nested_elt(self):
        src = """
        def test():
            return {{y for y in x} for x in lst}
        """
        expected = """
        def test():
            return set([set([y for y in x]) for x in lst])
        """
        utils.compare(src, expected, decomp.DeComp)
