'''
Created on Oct 14, 2014

@author: stefan
'''
import unittest
import ast
import itertools

import astor

import utils
import scoping

class TestLocalVariableCollector(unittest.TestCase):
    """
    Unit-tests for scopoing.LocalVariableCollector.
    """

    def scan_func(self, src):
        src = utils.unindent(src)
        root = ast.parse(src)
        func = next(node for node in root.body if isinstance(node, ast.FunctionDef) and node.name == "test")
        target = scoping.LocalVariableCollector()
        target.visit(func)
        return target

    def testAssignment(self):
        src = """
        def test():
            x = 1
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testRead(self):
        src = """
        def test():
            print x
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        self.assertIn("x", target.read_vars)
        
    def testGlobalRead(self):
        src = """
        def test():
            global x
            print x
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        self.assertIn("x", target.global_vars)
        self.assertIn("x", target.read_vars)
        
    def testGlobalAssignment(self):
        src = """
        def test():
            global x
            x = 1
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertIn("x", target.global_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testDel(self):
        src = """
        def test():
            del x
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)

    def testParam(self):
        src = """
        def test(x):
            pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testArgs(self):
        src = """
        def test(*x):
            pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testKwargs(self):
        src = """
        def test(**x):
            pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testFunction(self):
        src = """
        def test():
            def x():
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testFunction_default_args(self):
        src = """
        def test():
            def x(p=default_value):
                pass
        """
        target = self.scan_func(src)
        self.assertIn("default_value", target.read_vars)
        
    def testNoNestedFunction(self):
        src = """
        def test():
            def foo():
                x = 1
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
        
    def testClass(self):
        src = """
        def test():
            class x():
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testNoNestedClass(self):
        src = """
        def test():
            class foo():
                x = 1
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testImport(self):
        src = """
        def test():
            import x
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testImportGlobal(self):
        src = """
        def test():
            global x
            import x
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertIn("x", target.global_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testImportAs(self):
        src = """
        def test():
            import foo as x
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testFromImport(self):
        src = """
        def test():
            from foo import x
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
    
    def testFor(self):
        src = """
        def test():
            for x in foo:
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testExcept(self):
        src = """
        def test():
            try:
                pass
            except foo, x:
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testExceptAs(self):
        src = """
        def test():
            try:
                pass
            except foo as x:
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testWith(self):
        src = """
        def test():
            with foo as x:
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testLambda(self):
        src = """
        def test():
            lambda x:None
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testGenerator(self):
        src = """
        def test():
            (x for x in foo)
        """
        target = self.scan_func(src)
        self.assertNotIn("x", target.assigned_vars)
        
    def testListComp(self):
        src = """
        def test():
            [foo for x in foo]
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("foo", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)

    def testImportNested(self):
        src = """
        def test():
            import x.y
        """
        target = self.scan_func(src)
        self.assertIn("x", target.assigned_vars)
        self.assertNotIn("y", target.assigned_vars)
        self.assertNotIn("x", target.read_vars)
        
    def testDecorator(self):
        src = """
        def test():
            @decorum
            def foo():
                pass
        """
        target = self.scan_func(src)
        self.assertIn("decorum", target.read_vars)
        
    def testDecoratorArgs(self):
        src = """
        def test():
            @decorum(x)
            def foo():
                pass
        """
        target = self.scan_func(src)
        self.assertIn("x", target.read_vars)

class TestScopeAssigner(unittest.TestCase):
    """
    Unit tests for scoping.ScopeAssigner.
    
    All tests work like this:
    
    1. Hand-written an AST without scope information.
    2. Use scoping.ScopeAssigner on that AST.
    3. Compare with another hand-written AST that has the expected scope info.
    
    It would be ugly to write tests like that. So we
    
    * Write code instead of AST for convenience and readability.
    * Compare code instead of AST to make error messages easier to interpret.
    
    We encode scope information in the source by adding `_SCOPE` to the identifier.
    When we compare source we pass both through ast.parse and astor.to_source to
    avoid code formatting differences to affect the result.
    """

    def test_local(self):
        src = """
        def test():
            x = 1
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
        """
        self.compare(src, expected)

  
    def test_param(self):
        src = """
        def test(x):
            pass
        """
        expected = """
        def test_GLOBAL(x_LOCAL):
            pass
        """
        self.compare(src, expected)
        
    def test_default_args(self):
        src = """
        def test():
            def x(p=default_value):
                pass
        """
        expected = """
        def test_GLOBAL():
            def x_LOCAL(p_LOCAL=default_value_GLOBAL):
                pass
        """
        self.compare(src, expected)
        
    def test_args(self):
        src = """
        def test(*x):
            pass
        """
        expected = """
        def test_GLOBAL(*x_LOCAL):
            pass
        """
        self.compare(src, expected)
        
    def test_kwargs(self):
        src = """
        def test(**x):
            pass
        """
        expected = """
        def test_GLOBAL(**x_LOCAL):
            pass
        """
        self.compare(src, expected)
    
    def test_implicit_global(self):
        src = """
        def test():
            print x
        """
        expected = """
        def test_GLOBAL():
            print x_GLOBAL
        """
        self.compare(src, expected)
        
    def test_explicit_global(self):
        src = """
        def test():
            global x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            x_GLOBAL = 1
        """
        self.compare(src, expected)
        
    def test_free(self):
        src = """
        def test():
            def inner():
                print x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            def inner_LOCAL():
                print x_FREE
            x_LOCAL = 1
        """
        self.compare(src, expected)
        
    def test_nonfree(self):
        src = """
        def test():
            def inner():
                x = 1
            x = 1
        """
        expected = """
        def test_GLOBAL():
            def inner_LOCAL():
                x_LOCAL = 1
            x_LOCAL = 1
        """
        self.compare(src, expected)
        
    def test_class(self):
        src = """
        def test():
            class inner():
                pass
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                pass
        """
        self.compare(src, expected)

    def test_class_free(self):
        src = """
        def test():
            class inner():
                print x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                print x_FREE
            x_LOCAL = 1
        """
        self.compare(src, expected)
        

        
    def test_class_local(self):
        src = """
        def test():
            class inner():
                x = 1
            x = 1
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                x_LOCAL = 1
            x_LOCAL = 1
        """
        self.compare(src, expected)
        

    def test_class_member_free(self):
        src = """
        def test():
            class inner():
                x = 1
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                x_LOCAL = 1
                def foo_LOCAL():
                    print x_GLOBAL
        """
        self.compare(src, expected)
    
    def test_class_member_free2(self):
        src = """
        def test():
            x = 1
            class inner():
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
            class inner_LOCAL():
                def foo_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
        
    def test_class_member_free3(self):
        src = """
        def test():
            x = 1
            class inner():
                x = 2
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
            class inner_LOCAL():
                x_LOCAL = 2
                def foo_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
    
    def test_lambda(self):
        src = """
        def test():
            lambda x:0
        """
        expected = """
        def test_GLOBAL():
            lambda x_LOCAL:0
        """
        self.compare(src, expected)
        
    def test_lambda_free(self):
        src = """
        def test():
            x = 0
            lambda y:x
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 0
            lambda y_LOCAL:x_FREE
        """
        self.compare(src, expected)

    def test_generator(self):
        src = """
        def test():
            x = []
            (y+x for y in x)
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = []
            (y_LOCAL+x_FREE for y_LOCAL in x_FREE)
        """
        self.compare(src, expected)
        
    def test_import(self):
        src = """
        def test():
            import x
        """
        expected = """
        def test_GLOBAL():
            import x_LOCAL
        """
        self.compare(src, expected)
        
    def test_import_global(self):
        src = """
        def test():
            global x
            import x
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            import x_GLOBAL
        """
        self.compare(src, expected)

    def test_import_as(self):
        src = """
        def test():
            import x as y
        """
        expected = """
        def test_GLOBAL():
            import x as y_LOCAL
        """
        self.compare(src, expected)
        
    def test_import_as_nocollision(self):
        src = """
        def test():
            x = 1
            def inner():
                import x as y
                print x
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
            def inner_LOCAL():
                import x as y_LOCAL
                print x_FREE
        """
        self.compare(src, expected)
        
    def test_import_expression(self):
        src = """
        def test():
            import x.y
        """
        expected = """
        def test_GLOBAL():
            import x.y_LOCAL
        """
        self.compare(src, expected)

    def testExcept(self):
        src = """
        def test():
            try:
                pass
            except foo, x:
                pass
        """
        expected = """
        def test_GLOBAL():
            try:
                pass
            except foo_GLOBAL, x_LOCAL:
                pass
        """
        self.compare(src, expected)
        
    def testExceptAs(self):
        src = """
        def test():
            try:
                pass
            except foo as x:
                pass
        """
        expected = """
        def test_GLOBAL():
            try:
                pass
            except foo_GLOBAL as x_LOCAL:
                pass
        """
        self.compare(src, expected)

    def testExceptGlobal(self):
        src = """
        def test():
            global x
            try:
                pass
            except foo, x:
                pass
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            try:
                pass
            except foo_GLOBAL, x_GLOBAL:
                pass
        """
        self.compare(src, expected)
        
    def testDecorator(self):
        src = """
        def test():
            @decorum
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            @decorum_GLOBAL
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)
        
    def testDecoratorLocal(self):
        src = """
        def test():
            decorum = 1
            @decorum
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            decorum_LOCAL = 1
            @decorum_LOCAL
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)
        
    def testDecoratorArgs(self):
        src = """
        def test():
            x = 1
            @decorum(x)
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
            @decorum_GLOBAL(x_LOCAL)
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)

    def compare(self, src, expected_src):
        actual_root = ast.parse(utils.unindent(src))
        scoping.ScopeAssigner().visit(actual_root)
        EncodeScopeInIdentifier().visit(actual_root)
        actual_src = astor.to_source(actual_root)
        
        expected_root = ast.parse(utils.unindent(expected_src))
        expected_src = astor.to_source(expected_root)
                
        cmps = itertools.izip_longest(expected_src.splitlines(), actual_src.splitlines())
        for linenr, c in enumerate(cmps, 1):
            expected_line = c[0]
            actual_line = c[1]
            self.assertEqual(expected_line, actual_line, "Line %s differs. Expected %s but got %s." % (linenr, repr(expected_line), repr(actual_line)))
        


class TestExtendedScopeAssigner(unittest.TestCase):
    """
    Unit tests for scoping.ExtendedScopeAssigner.
    
    All tests work like this:
    
    1. Hand-written an AST without scope information.
    2. Use scoping.ScopeAssigner on that AST.
    3. Compare with another hand-written AST that has the expected scope info.
    
    It would be ugly to write tests like that. So we
    
    * Write code instead of AST for convenience and readability.
    * Compare code instead of AST to make error messages easier to interpret.
    
    We encode scope information in the source by adding `_SCOPE` to the identifier.
    When we compare source we pass both through ast.parse and astor.to_source to
    avoid code formatting differences to affect the result.
    """

    def test_local(self):
        src = """
        def test():
            x = 1
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
        """
        self.compare(src, expected)

  
    def test_param(self):
        src = """
        def test(x):
            pass
        """
        expected = """
        def test_GLOBAL(x_LOCAL):
            pass
        """
        self.compare(src, expected)
        
    def test_default_args(self):
        src = """
        def test():
            def x(p=default_value):
                pass
        """
        expected = """
        def test_GLOBAL():
            def x_LOCAL(p_LOCAL=default_value_GLOBAL):
                pass
        """
        self.compare(src, expected)
        
    def test_args(self):
        src = """
        def test(*x):
            pass
        """
        expected = """
        def test_GLOBAL(*x_LOCAL):
            pass
        """
        self.compare(src, expected)
        
    def test_kwargs(self):
        src = """
        def test(**x):
            pass
        """
        expected = """
        def test_GLOBAL(**x_LOCAL):
            pass
        """
        self.compare(src, expected)
    
    def test_implicit_global(self):
        src = """
        def test():
            print x
        """
        expected = """
        def test_GLOBAL():
            print x_GLOBAL
        """
        self.compare(src, expected)
        
    def test_explicit_global(self):
        src = """
        def test():
            global x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            x_GLOBAL = 1
        """
        self.compare(src, expected)
        
    def test_free(self):
        src = """
        def test():
            def inner():
                print x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            def inner_LOCAL():
                print x_FREE
            x_SHARED = 1
        """
        self.compare(src, expected)
        
    def test_nonfree(self):
        src = """
        def test():
            def inner():
                x = 1
            x = 1
        """
        expected = """
        def test_GLOBAL():
            def inner_LOCAL():
                x_LOCAL = 1
            x_LOCAL = 1
        """
        self.compare(src, expected)
        
    def test_class(self):
        src = """
        def test():
            class inner():
                pass
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                pass
        """
        self.compare(src, expected)

    def test_class_free(self):
        src = """
        def test():
            class inner():
                print x
            x = 1
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                print x_FREE
            x_SHARED = 1
        """
        self.compare(src, expected)
        
    def test_class_local(self):
        src = """
        def test():
            class inner():
                x = 1
            x = 1
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                x_LOCAL = 1
            x_LOCAL = 1
        """
        self.compare(src, expected)
        

    def test_class_member_free(self):
        src = """
        def test():
            class inner():
                x = 1
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            class inner_LOCAL():
                x_LOCAL = 1
                def foo_LOCAL():
                    print x_GLOBAL
        """
        self.compare(src, expected)
        
    def test_class_member_free2(self):
        src = """
        def test():
            x = 1
            class inner():
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 1
            class inner_LOCAL():
                def foo_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
        
    def test_class_member_free3(self):
        src = """
        def test():
            x = 1
            class inner():
                x = 2
                def foo():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 1
            class inner_LOCAL():
                x_LOCAL = 2
                def foo_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
    
    def test_lambda(self):
        src = """
        def test():
            lambda x:0
        """
        expected = """
        def test_GLOBAL():
            lambda x_LOCAL:0
        """
        self.compare(src, expected)
        
    def test_lambda_free(self):
        src = """
        def test():
            x = 0
            lambda y:x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 0
            lambda y_LOCAL:x_FREE
        """
        self.compare(src, expected)

    def test_generator(self):
        src = """
        def test():
            x = []
            (y+x for y in x)
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = []
            (y_LOCAL+x_FREE for y_LOCAL in x_FREE)
        """
        self.compare(src, expected)
        
    def test_import(self):
        src = """
        def test():
            import x
        """
        expected = """
        def test_GLOBAL():
            import x_LOCAL
        """
        self.compare(src, expected)
        
    def test_import_global(self):
        src = """
        def test():
            global x
            import x
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            import x_GLOBAL
        """
        self.compare(src, expected)

    def test_import_as(self):
        src = """
        def test():
            import x as y
        """
        expected = """
        def test_GLOBAL():
            import x as y_LOCAL
        """
        self.compare(src, expected)
        
    def test_import_as_nocollision(self):
        src = """
        def test():
            x = 1
            def inner():
                import x as y
                print x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 1
            def inner_LOCAL():
                import x as y_LOCAL
                print x_FREE
        """
        self.compare(src, expected)
        
    def test_import_expression(self):
        src = """
        def test():
            import x.y
        """
        expected = """
        def test_GLOBAL():
            import x.y_LOCAL
        """
        self.compare(src, expected)

    def test_passthrough(self):
        src = """
        def test():
            x = 1
            def middle():
                def inner():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 1
            def middle_LOCAL():
                def inner_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
        
    def test_middle(self):
        src = """
        def test():
            x = 1
            def middle():
                print x
                def inner():
                    print x
        """
        expected = """
        def test_GLOBAL():
            x_SHARED = 1
            def middle_LOCAL():
                print x_FREE
                def inner_LOCAL():
                    print x_FREE
        """
        self.compare(src, expected)
        
    def testExcept(self):
        src = """
        def test():
            try:
                pass
            except foo, x:
                pass
        """
        expected = """
        def test_GLOBAL():
            try:
                pass
            except foo_GLOBAL, x_LOCAL:
                pass
        """
        self.compare(src, expected)
        
    def testExceptAs(self):
        src = """
        def test():
            try:
                pass
            except foo as x:
                pass
        """
        expected = """
        def test_GLOBAL():
            try:
                pass
            except foo_GLOBAL as x_LOCAL:
                pass
        """
        self.compare(src, expected)

    def testExceptGlobal(self):
        src = """
        def test():
            global x
            try:
                pass
            except foo, x:
                pass
        """
        expected = """
        def test_GLOBAL():
            global x_GLOBAL
            try:
                pass
            except foo_GLOBAL, x_GLOBAL:
                pass
        """
        self.compare(src, expected)
        
    def testDecorator(self):
        src = """
        def test():
            @decorum
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            @decorum_GLOBAL
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)
        
    def testDecoratorLocal(self):
        src = """
        def test():
            decorum = 1
            @decorum
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            decorum_LOCAL = 1
            @decorum_LOCAL
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)
        
    def testDecoratorArgs(self):
        src = """
        def test():
            x = 1
            @decorum(x)
            def foo():
                pass
        """
        expected = """
        def test_GLOBAL():
            x_LOCAL = 1
            @decorum_GLOBAL(x_LOCAL)
            def foo_LOCAL():
                pass
        """
        self.compare(src, expected)

    def compare(self, src, expected_src):
        actual_root = ast.parse(utils.unindent(src))
        scoping.ScopeAssigner().visit(actual_root)
        scoping.ExtendedScopeAssigner().visit(actual_root)
        EncodeScopeInIdentifier().visit(actual_root)
        actual_src = astor.to_source(actual_root)
        
        expected_root = ast.parse(utils.unindent(expected_src))
        expected_src = astor.to_source(expected_root)
                
        cmps = itertools.izip_longest(expected_src.splitlines(), actual_src.splitlines())
        for linenr, c in enumerate(cmps, 1):
            expected_line = c[0]
            actual_line = c[1]
            self.assertEqual(expected_line, actual_line, "Line %s differs. Expected %s but got %s." % (linenr, repr(expected_line), repr(actual_line)))
        



class EncodeScopeInIdentifier(ast.NodeVisitor):
    """
    Renames identifier that have a scope assigned so that the scope becomes part
    of the variable name.
    This typically changes the behavior of the code and is really only intended to make the scope visible for testing purposes.
    """ 
    
    def encode(self, node, field):
        identifiers = getattr(node, field)
        scopes = getattr(node, field + "_scope")
        if isinstance(identifiers, list):
            encoded = [identifier + "_" + scope.value for identifier, scope in itertools.izip(identifiers, scopes)]
        else:
            encoded = identifiers + "_" + scopes.value
        setattr(node, field, encoded)
        
    
    def visit(self, node):
        for field in node._fields:
            if hasattr(node, field + "_scope"):
                self.encode(node, field)
        return ast.NodeVisitor.visit(self, node)
