# Copyright (C) 2015 Stefan C. Mueller

import unittest
import saneitizer
import ast
from pydron.translation import utils, naming
import astor
import sys
import StringIO as stringio

class TestSaneitizer(unittest.TestCase):
    
    def test_print_le_table(self):
        print saneitizer.Saneitizer.feature_table()


    def testPrint(self):
        src = """
        print "Hello World!"
        """
        self.execute(src, "Hello World!")

    def testFunc(self):
        src = """
        def foo():
            print "Hello"
        foo()
        """
        self.execute(src, "Hello")

    def testLocalVars(self):
        src = """
        def foo():
            a = 1
            b = 2
            print a + b
        foo()
        """
        self.execute(src, "3")

    def testClosure(self):
        src = """
        def outer():
            x = 1
            def inner():
                print x
            inner()
        outer()
        """
        self.execute(src, "1")
        
    def testLambda(self):
        src = """
        def test():
            f = lambda x,y:x+y
            print f(4,5)
        test()
        """
        self.execute(src, "9")
        
    def testGenerator(self):
        src = """
        def test():
            print ",".join(str(x**2) for x in [1,2,3])
        test() 
        """
        self.execute(src, "1,4,9")
        
    def testGenerator_if(self):
        src = """
        def test():
            print "[" + ",".join(str(x**2) for x in [1,2,3] if x > 1) + "]"
        test() 
        """
        self.execute(src, "[4,9]")
        
    def testGenerator_ifif(self):
        src = """
        def test():
            print "[" + ",".join(str(x**2) for x in [1,2,3] if x > 1 if x < 3) + "]"
        test() 
        """
        self.execute(src, "[4]")
        
    def testGenerator_forfor(self):
        src = """
        def test():
            print "[" + ",".join(str(x+y) for x in [1,2,3] for y in [10,20,30]) + "]"
        test() 
        """
        self.execute(src, "[11,21,31,12,22,32,13,23,33]")
                
    def testListComp(self):
        src = """
        def test():
            print [str(x) for x in [1,2,3]]
        test() 
        """
        self.execute(src, "2")
        
    def testSetComp(self):
        src = """
        def test():
            print {str(x) for x in [1,2,3]}
        test() 
        """
        self.execute(src, "2")
        
    def testDictComp(self):
        src = """
        def test():
            print {str(x):x for x in [1,2,3]}
        test() 
        """
        self.execute(src, "2")
        
    def testUnbound(self):
        src = """
        def test():
            try:
                return x
            except UnboundLocalError:
                print "unbound"
            x = 1
        test() 
        """
        self.execute(src, "unbound")
        
    def testUnboundDel(self):
        src = """
        def test():
            x = 1
            del x
            try:
                return x
            except UnboundLocalError:
                print "unbound"
        test() 
        """
        self.execute(src, "unbound")
        
    def testClass(self):
        src = """
        def test():
            class X(object):
                print "hello"
        test() 
        """
        self.execute(src, "hello")
        
    def testClassMember(self):
        src = """
        def test():
            class X(object):
                def foo(self):
                    print "hello"
            return X()
        test().foo()
        """
        self.execute(src, "hello")
        
    def testClassMemberDelete(self):
        src = """
        def test3():
            class X(object):
                member = 1
                del member
            x = X()
            print hasattr(x, 'member')
        test3()
        """
        self.execute(src, "False")
        
    def testClassClosure(self):
        src = """
        def test():
            x = "hello"
            class X(object):
                def foo(self):
                    print x
            return X()
        test().foo()
        """
        self.execute(src, "hello")
        
    def testClassClosureScoping(self):
        src = """
        def test():
            x = "hello"
            class X(object):
                x = "class scope not visible to members"
                def foo(self):
                    print x
            return X()
        test().foo()
        """
        self.execute(src, "hello")
        
    def test_default(self):
        src = """
        def test(a="hello"):
            print a
        test()
        """
        self.execute(src, "hello")
        
    def test_default_one(self):
        src = """
        def test(a="hello"):
            print a
        test("world")
        """
        self.execute(src, "world")
        
    def test_default_kwarg(self):
        src = """
        def test(a=1, b=2):
            print a, b
        test("hello", b="world")
        """
        self.execute(src, "hello world")
        
    def test_default_kwargs(self):
        src = """
        def test(a,b,c=1,**kwargs):
            print a, b
        test(1,2,foo=3)
        """
        self.execute(src, "1 2")
        
    def test_default_args(self):
        src = """
        def test(a,b,c=1,*args, **kwargs):
            print " ".join(args)
        test("1","2","3","4","5")
        """
        self.execute(src, "4 5")
        
    def test_print_nonewline(self):
        src = """
        print "hello",
        print "world"
        """
        self.execute(src, "hello world")
        
    def test_print_space(self):
        src = """
        print "hello\t", "world"
        """
        self.execute(src, "hello\tworld")
        
    def test_print_memory(self):
        src = """
        print "hello",
        print "world"
        """
        self.execute(src, "hello world")

    def test_break(self):
        src = """
        def test():
            for i in range(10):
                print i,
                if i == 5:
                    break
            print "x"
        test()
        """
        self.execute(src, "0 1 2 3 4 5 x")
        
    def test_continue(self):
        src = """
        def test():
            for i in range(10):
                if i % 2 == 1:
                    continue
                print i,
            print "x"
        test()
        """
        self.execute(src, "0 2 4 6 8 x")
        
    def test_return(self):
        src = """
        def test():
            for i in range(10):
                print i,
                if i == 5:
                    return 
            print "x"
        test()
        """
        self.execute(src, "0 1 2 3 4 5")
    
    def test_break_else(self):
        src = """
        def test():
            for i in range(10):
                print i,
                if i == 5:
                    break
            else:
                print "y",
            print "x",
        test()
        """
        self.execute(src, "0 1 2 3 4 5 x")
    
    def test_else(self):
        src = """
        def test():
            for i in range(10):
                print i,
                if i == 11:
                    break
            else:
                print "y",
            print "x",
        test()
        """
        self.execute(src, "0 1 2 3 4 5 6 7 8 9 y x")
        

    def execute(self, src, output_contains=None):
        src = utils.unindent(src)
        
        expected = self._run(src)
        
        node = ast.parse(src)
        node = saneitizer.Saneitizer().process(node)
        naming.MakeIdsValid().visit(node)
        
        transformed_code = astor.to_source(node)
        
        pydron_builtins = "from pydron.translation.builtins import *"
        transformed_code = pydron_builtins + "\n\n" + transformed_code
        
        try:
            # just to see if it compiles
            compile(node, "[string]", 'exec')
            
            # we actually use the source code to run
            actual = self._run(transformed_code)
            
            self.assertEqual(actual, expected)
            if output_contains:
                self.assertIn(output_contains, actual)
        except:
            sys.stderr.write(transformed_code)
            sys.stderr.write("\n\n")
            raise

    def _run(self, code):
        buffer_stdout = stringio.StringIO()
        orig_stdout = sys.stdout
        sys.stdout = buffer_stdout
        
        exec(code, {})
        
        sys.stdout = orig_stdout
        stdout = buffer_stdout.getvalue()
        return stdout
        
        
    
    