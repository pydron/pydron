# Copyright (C) 2014 Stefan C. Mueller

import unittest

from pydron.translation import utils, dewith

class TestDeWith(unittest.TestCase):

    def test_noas(self):
        src = """
        def test():
            with foo:
                x + y
        """
        expected = """
        def test():
            mgr__U0 = foo
            exit__U0 = type(mgr__U0).__exit__
            value__U0 = type(mgr__U0).__enter__(mgr__U0)
            exc__U0 = True
            try:
                try:
                    x + y
                except:
                    exc__U0 = False
                    if not exit__U0(mgr__U0, *sys.exc_info()):
                        raise
            finally:
                if exc__U0:
                    exit__U0(mgr__U0, None, None, None)
        """
        utils.compare(src, expected, dewith.DeWith)

    def test_as(self):
        src = """
        def test():
            with foo as bar:
                x + y
        """
        expected = """
        def test():
            mgr__U0 = foo
            exit__U0 = type(mgr__U0).__exit__
            value__U0 = type(mgr__U0).__enter__(mgr__U0)
            exc__U0 = True
            try:
                try:
                    bar = value__U0
                    x + y
                except:
                    exc__U0 = False
                    if not exit__U0(mgr__U0, *sys.exc_info()):
                        raise
            finally:
                if exc__U0:
                    exit__U0(mgr__U0, None, None, None)
        """
        utils.compare(src, expected, dewith.DeWith)

