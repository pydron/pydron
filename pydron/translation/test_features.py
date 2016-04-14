# Copyright (C) 2015 Stefan C. Mueller

import ast
import unittest

from pydron.translation import features, scoping, utils

class AbstractFeatureTest(object):
    
    def assertHasFeature(self, src):
        self.assertTrue(self._check(src), "Expected code to have feature %s" % self.check)
    
    def assertFeatureAbsent(self, src):
        self.assertFalse(self._check(src), "Expected code NOT to have feature %s" % self.check)
    
    def _check(self, src):
        node = ast.parse(utils.unindent(src))
        utils.EncodeNames().visit(node)
        scoping.ScopeAssigner().visit(node)
        scoping.ExtendedScopeAssigner().visit(node)
        return self.check(node)

class TestBreak(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_break)
    
    def test_no_break(self):
        src = """
        for x in []:
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_for_break(self):
        src = """
        for x in []:
            break
            y = 1
        """
        self.assertHasFeature(src)
        
    def test_for_finalbreak(self):
        src = """
        for x in []:
            y = 1
            if True:
                break
        """
        self.assertFeatureAbsent(src)
        
    def test_while_break(self):
        src = """
        while True:
            break
            y = 1
        """
        self.assertHasFeature(src)
        
        
    def test_while_finalbreak(self):
        src = """
        while True:
            y = 1
            if True:
                break
        """
        self.assertFeatureAbsent(src)
 
 
class TestContinue(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_continue)
    
    def test_no_continue(self):
        src = """
        for x in []:
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_continue(self):
        src = """
        def foo():
            continue
            y = 1
        """
        self.assertHasFeature(src)
        

class TestReturn(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_return)
    
    def test_no_return(self):
        src = """
        for x in []:
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_return(self):
        src = """
        def foo():
            return 1
            y = 1
        """
        self.assertHasFeature(src)
        
    def test_final(self):
        src = """
        def foo():
            y = 1
            return 1
        """
        self.assertFeatureAbsent(src)
        
class TestDefaultValues(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_funcdefaultvalues)
    
    def test_absent(self):
        src = """
        def f(x):
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        def f(x=1):
            pass
        """
        self.assertHasFeature(src)


class TestNonExplicitMembers(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_nonexplicitmembers)
    
    def test_absent(self):
        src = """
        class C(object):
            __pydron_members__ = locals()
        """
        self.assertFeatureAbsent(src)
        
    def test_present_no_member(self):
        src = """
        class C(object):
            pass
        """
        self.assertHasFeature(src)

    def test_present_member(self):
        src = """
        class C(object):
            x = 1
        """
        self.assertHasFeature(src)


class TestLocals(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_locals)
    
    def test_absent(self):
        src = """
        x = f(1)
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        x = locals()
        """
        self.assertHasFeature(src)



class TestDecorator(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_decorator)
    
    def test_class_absent(self):
        src = """
        class C(object):
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_class_present(self):
        src = """
        @f
        class C(object):
            pass
        """
        self.assertHasFeature(src)
        
    def test_function_absent(self):
        src = """
        def f():
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_function_present(self):
        src = """
        @f
        def f():
            pass
        """
        self.assertHasFeature(src)
        

class TestComplexExpr(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_complexexpr)
    
    def test_absent_num(self):
        src = """
        x = f(1)
        """
        self.assertFeatureAbsent(src)
        
    def test_absent_str(self):
        src = """
        x = f("str")
        """
        self.assertFeatureAbsent(src)
        
    def test_absent_Name(self):
        src = """
        x = f(y)
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        x = 1 + 2 * 3
        """
        self.assertHasFeature(src)
    
    def test_default(self):
        src = """
        def f(x=1+2):
            pass
        """
        self.assertHasFeature(src)

class TestMultitarget(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_multitarget)
    
    def test_absent(self):
        src = """
        x = 1
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        x = y = 1
        """
        self.assertHasFeature(src)
        

class TestClosureFunc(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_closure_func)
    
    def test_absent(self):
        src = """
        def outer():
            x = 1
            def inner():
                x = 1
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        def outer():
            x = 1
            def inner():
                print x
        """
        self.assertHasFeature(src)
        
        
    def test_shared_in_class(self):
        src = """
        class outer():
            x = 1
            def inner():
                print x
        """
        self.assertFeatureAbsent(src)
        
    def test_shared_outside_class(self):
        src = """
        def outer():
            x = 1
            class c():
                def inner():
                    print x
        """
        self.assertHasFeature(src)
        
    def test_free_in_class(self):
        src = """
        def outer():
            x = 1
            class inner():
                print x
        """
        self.assertFeatureAbsent(src)
        
        
        
class TestClosureClass(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_closure_class)
    
    def test_absent(self):
        src = """
        def outer():
            x = 1
            def inner():
                x = 1
        """
        self.assertFeatureAbsent(src)
        
    def test_free_in_class(self):
        src = """
        def outer():
            x = 1
            class inner():
                print x
        """
        self.assertHasFeature(src)
        
    def test_shared_in_class(self):
        src = """
        class outer():
            x = 1
            def inner():
                print x
        """
        self.assertFeatureAbsent(src)
        
    def test_functions(self):
        src = """
        def outer():
            x = 1
            def inner():
                print x
        """
        self.assertFeatureAbsent(src)

class TestUnassignedPassthrough(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_unassigned_passthrough)
    
    def test_absent_param(self):
        src = """
        def c(x__P0):
            inner = f(x__P0)         
        """
        self.assertFeatureAbsent(src)
        
    def test_absent_assigned(self):
        src = """
        def c():
            x__P0 = 123
            inner = f(x__P0)         
        """
        self.assertFeatureAbsent(src)
        
    def test_present(self):
        src = """
        class c(object):
            inner = f(x__P0)         
        """
        self.assertHasFeature(src)
        
class TestGlobal(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_global)
    
    def test_global_func_in_module(self):
        src = """
        def f():
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_var_func_in_module(self):
        src = """
        def f():
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_builtin(self):
        src = """
        def f():
            __pydron_f__()
        """
        self.assertFeatureAbsent(src)
        
    def test_local_vars(self):
        src = """
        def f():
            x = 1
            print x
        """
        self.assertFeatureAbsent(src)
        
    def test_global_var(self):
        src = """
        def f():
            print x
        """
        self.assertHasFeature(src)
        
        
    def test_explicit_global(self):
        src = """
        def f():
            x = 1
            print x
            global x
        """
        self.assertHasFeature(src)
        
        
    def test_free_var(self):
        src = """
        def outer():
            x = 1
            def inner():
                print x
        """
        self.assertFeatureAbsent(src)
        
    def test_None(self):
        src = """
        def outer():
            return None
        """
        self.assertFeatureAbsent(src)
        
    def test_True(self):
        src = """
        def outer():
            return True
        """
        self.assertFeatureAbsent(src)
        
    def test_False(self):
        src = """
        def outer():
            return False
        """
        self.assertFeatureAbsent(src)
        
    def test_param(self):
        src = """
        def outer(x):
            pass
        """
        self.assertFeatureAbsent(src)
        
    def test_default_arg(self):
        src = """
        def outer(x=y):
            pass
        """
        self.assertFeatureAbsent(src)
        
class TestDeleteVar(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_deletevar)
    
    def test_delete_local_var(self):
        src = """
        def f():
            x = 1
            del x
        """
        self.assertHasFeature(src)
        
    def test_delete_global_var(self):
        src = """
        x = 1
        del x
        """
        self.assertHasFeature(src)
        
    def test_delete_global_var_explicit(self):
        src = """
        def outer():
            global x
            del x
        """
        self.assertHasFeature(src)
        
    def test_delete_attr(self):
        src = """
        def f():
            del x.y
        """
        self.assertFeatureAbsent(src)
        
    def test_delete_subscript(self):
        src = """
        def f():
            del x[0]
        """
        self.assertFeatureAbsent(src)
        

class TestOverwrite(unittest.TestCase, AbstractFeatureTest):
    
    check = staticmethod(features.check_overwrite)
    
    def test_single_assignments(self):
        src = """
        def f():
            x = 1
            y = 1
        """
        self.assertFeatureAbsent(src)
        
    def test_reassignment(self):
        src = """
        def f():
            x = 1
            x = 1
        """
        self.assertHasFeature(src)
        
    def test_same_name_local_vars(self):
        src = """
        def f():
            x = 1
            def g():
                x = 1
        """
        self.assertFeatureAbsent(src)
        
    def test_func_name(self):
        src = """
        def f():
            x = 1
            def x():
                pass
        """
        self.assertHasFeature(src)
        
    def test_class_name(self):
        src = """
        def f():
            x = 1
            class x():
                pass
        """
        self.assertHasFeature(src)
        
    def test_param(self):
        src = """
        def f(x):
            x = 1
        """
        self.assertHasFeature(src)
        
    def test_args(self):
        src = """
        def f(*x):
            x = 1
        """
        self.assertHasFeature(src)
        
    def test_kwargs(self):
        src = """
        def f(**x):
            x = 1
        """
        self.assertHasFeature(src)
        
    def test_except(self):
        src = """
        def f():
            x = 1
            try:
                pass
            except ValueError as x:
                pass
        """
        self.assertHasFeature(src)
        