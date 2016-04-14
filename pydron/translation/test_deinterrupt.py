# Copyright (C) 2014 Stefan C. Mueller

import unittest

from pydron.translation import utils
from pydron.translation.deinterrupt import DeInterrupt


class TestDeInterrupt(unittest.TestCase):

    def test_add_return(self):
        src = """
        def test():
            pass
        """
        expected = """
        def test():
            pass
            return None
        """
        utils.compare(src, expected, DeInterrupt)

    def test_return(self):
        src = """
        def test():
            return "Hello"
        """
        expected = """
        def test():
            returnvalue__U0 = 'Hello'
            interrupted__U0 = '3_return'
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_return_inside_if(self):
        src = """
        def test():
            if True:
                return "Hello"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            if True:
                returnvalue__U0 = 'Hello'
                interrupted__U0 = "3_return"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)

    def test_return_skip(self):
        src = """
        def test():
            if True:
                return "Hello"
            print "not always executed"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            if True:
                returnvalue__U0 = 'Hello'
                interrupted__U0 = '3_return'
            if interrupted__U0 == "0_none":
                print "not always executed"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_return_skip_nested(self):
        src = """
        def test():
            if a:
                if b:
                    return "Hello"
                print "a"
            print "b"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            if a:
                interrupted__U0 = "0_none"
                if b:
                    returnvalue__U0 = 'Hello'
                    interrupted__U0 = '3_return'
                if interrupted__U0 == "0_none":
                    print "a"
            if interrupted__U0 == "0_none":
                print "b"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for(self):
        src = """
        def test():
            for a in b:
                pass
        """
        expected = """
        def test():
            for a in b:
                pass
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_continue(self):
        src = """
        def test():
            for a in b:
                continue
        """
        expected = """
        def test():
            for a in b:
                interrupted__U0 = "1_continue"
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_continue_jump(self):
        src = """
        def test():
            for a in b:
                continue
                print "hi"
        """
        expected = """
        def test():
            for a in b:
                interrupted__U0 = "1_continue"
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_continue_if_jump(self):
        src = """
        def test():
            for a in b:
                if a:
                    continue
                print "hi"
        """
        expected = """
        def test():
            for a in b:
                interrupted__U0 = "0_none"
                if a:
                    interrupted__U0 = "1_continue"
                if interrupted__U0 == "0_none":
                    print "hi"
                if interrupted__U0 == "1_continue":
                    interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_break(self):
        src = """
        def test():
            for a in b:
                break
                print "hi"
        """
        expected = """
        def test():
            interrupted__U0 = "0_none"
            for a in b:
                interrupted__U0 = "2_break"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "2_break":
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_break_continue(self):
        src = """
        def test():
            for a in b:
                if a:
                    break
                if b:
                    continue
                print "hi"
        """
        expected = """
        def test():
            interrupted__U0 = "0_none"
            for a in b:
                interrupted__U0 = "0_none"
                if a:
                    interrupted__U0 = "2_break"
                if interrupted__U0 == "0_none":
                    interrupted__U0 = "0_none"
                    if b:
                        interrupted__U0 = "1_continue"
                    if interrupted__U0 == "0_none":
                        print "hi"
                if interrupted__U0 == "1_continue":
                    interrupted__U0 = "0_none"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "2_break":
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_break_if(self):
        src = """
        def test():
            for a in b:
                if a:
                    break
                print "hi"
        """
        expected = """
        def test():
            interrupted__U0 = "0_none"
            for a in b:
                interrupted__U0 = "0_none"
                if a:
                    interrupted__U0 = "2_break"
                if interrupted__U0 == "0_none":
                    print "hi"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "2_break":
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_break_else(self):
        src = """
        def test():
            for a in b:
                break
            else:
                print "hi"
        """
        expected = """
        def test():
            interrupted__U0 = "0_none"
            for a in b:
                interrupted__U0 = "2_break"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "0_none":
                print "hi"
            elif interrupted__U0 == "2_break":
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_for_else(self):
        src = """
        def test():
            for a in b:
                print "hi"
            else:
                print "HI"
        """
        expected = """
        def test():
            for a in b:
                print "hi"
            print "HI"
            return None
        """
        utils.compare(src, expected, DeInterrupt)

    def test_for_return(self):
        src = """
        def test():
            for a in b:
                return
            print "hi"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            for a in b:
                returnvalue__U0 = None
                interrupted__U0 = "3_return"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "0_none":
                print "hi"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)

    def test_for_return_else(self):
        src = """
        def test():

            for a in b:
                return
            else: 
                print "hi"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            for a in b:
                returnvalue__U0 = None
                interrupted__U0 = "3_return"
                if ((interrupted__U0 == '2_break') or (interrupted__U0 == '3_return')):
                    break
            if interrupted__U0 == "0_none":
                print "hi"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_while(self):
        src = """
        def test():
            while a:
                print "hi"
        """
        expected = """
        def test():
            while a:
                print "hi"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
        
    def test_while_continue(self):
        src = """
        def test():
            while a:
                if b:
                    continue
                print "hi"
        """
        expected = """
        def test():
            while a:
                interrupted__U0 = "0_none"
                if b:
                    interrupted__U0 = "1_continue"
                if interrupted__U0 == "0_none":
                    print "hi"
                if interrupted__U0 == "1_continue":
                    interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)

    def test_while_break(self):
        src = """
        def test():
            while a:
                if b:
                    break
                print "hi"
        """
        expected = """
        def test():
            interrupted__U0 = "0_none"
            while interrupted__U0 == "0_none" and a:
                interrupted__U0 = "0_none"
                if b:
                    interrupted__U0 = "2_break"
                if interrupted__U0 == "0_none":
                    print "hi"
            if interrupted__U0 == "2_break":
                interrupted__U0 = "0_none"
            return None
        """
        utils.compare(src, expected, DeInterrupt)
    
    def test_With(self):
        src = """
        def test():
            with a:
                return x
            print "hi"
        """
        expected = """
        def test():
            with a:
                returnvalue__U0 = x
                interrupted__U0 = "3_return"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)

    def test_tryexcept(self):
        src = """
        def test():
            try:
                return "hi"
            except:
                print "hello"
            print "world"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            try:
                returnvalue__U0 = "hi"
                interrupted__U0 = "3_return"
            except:
                print "hello"
            if interrupted__U0 == "0_none":
                print "world"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)

        
    def test_tryexcept_inexcept(self):
        src = """
        def test():
            try:
                print "hi"
            except:
                return "hello"
            print "world"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            try:
                print "hi"
            except:
                returnvalue__U0 = "hello"
                interrupted__U0 = "3_return"
            if interrupted__U0 == "0_none":
                print "world"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)

    def test_tryfinally(self):
        src = """
        def test():
            try:
                return "hi"
            finally:
                return "hello"
            print "world"
        """
        expected = """
        def test():
            returnvalue__U0 = None
            interrupted__U0 = "0_none"
            try:
                returnvalue__U0 = "hi"
                interrupted__U0 = "3_return"
            finally:
                interrupted__U1 = interrupted__U0
                returnvalue__U0 = "hello"
                interrupted__U0 = "3_return"
                interrupted__U0 = __pydron_max__(interrupted__U0, interrupted__U1)
            if interrupted__U0 == "0_none":
                print "world"
            return returnvalue__U0
        """
        utils.compare(src, expected, DeInterrupt)


