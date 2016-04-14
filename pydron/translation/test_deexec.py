# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.translation import utils, deexec


class TestDeExec(unittest.TestCase):

    def test_exec(self):
        src = """
        exec "code"
        """
        expected = """
        __pydron_exec__("code", locals(), globals())
        """
        utils.compare(src, expected, deexec.DeExec)


    def test_locals(self):
        src = """
        exec "code" in context
        """
        expected = """
        __pydron_exec__("code", None, context)
        """
        utils.compare(src, expected, deexec.DeExec)

    def test_locals_globals(self):
        src = """
        exec "code" in context, context2
        """
        expected = """
        __pydron_exec__("code", context2, context)
        """
        utils.compare(src, expected, deexec.DeExec)