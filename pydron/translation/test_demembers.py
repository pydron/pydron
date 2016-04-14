# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, demembers


class DeMembers(unittest.TestCase):

    def test_simple(self):
        src = """
        class Test():
            x = 1
        """
        expected = """
        class Test():
            x = 1
            __pydron_members__ = locals()
        """
        utils.compare(src, expected, demembers.DeMembers)

