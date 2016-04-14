# Copyright (C) 2014 Stefan C. Mueller

import unittest
from pydron.translation import utils, decomplexexpr


class TestDeComplexExpr(unittest.TestCase):
    
    def test_binop_single(self):
        src = """
        x = 1 + 2
        """
        expected = """
        x = 1 + 2
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_binop(self):
        src = """
        x = 1 + 2 * 3
        """
        expected = """
        binop__U0 = 2 * 3
        x = 1 + binop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_unaryop(self):
        src = """
        x = -(1+2)
        """
        expected = """
        binop__U0 = 1 + 2
        x = - (binop__U0)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_augassign_simple(self):
        src = """
        x += "s"
        """
        expected = """
        x += "s"
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_augassign(self):
        src = """
        x += "s" + "t"
        """
        expected = """
        binop__U0 = "s" + "t"
        x += binop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_return(self):
        src = """
        def f():
            return "s" + "t"
        """
        expected = """
        def f():
            binop__U0 = "s" + "t"
            return binop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_delete_single(self):
        src = """
        del x[0]
        """
        expected = """
        del x[0]
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_delete(self):
        src = """
        del x[1 + 2]
        """
        expected = """
        binop__U0 = 1 + 2
        del x[binop__U0]
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_and(self):
        src = """
        x = a and b
        """
        expected = """
        if a:
            boolop__U0 = b
        else:
            boolop__U0 = a
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_and3(self):
        src = """
        x = a and b and c
        """
        expected = """
        if a:
            if b:
                boolop__U0 = c
            else:
                boolop__U0 = b
        else:
            boolop__U0 = a
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_and3_expr(self):
        src = """
        x = a and b+c and d
        """
        expected = """
        if a:
            binop__U0 = b+c
            if binop__U0:
                boolop__U0 = d
            else:
                boolop__U0 = binop__U0
        else:
            boolop__U0 = a
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_or3(self):
        src = """
        x = a or b or c
        """
        expected = """
        if a:
            boolop__U0 = a
        elif b:
            boolop__U0 = b
        else:
            boolop__U0 = c
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_or(self):
        src = """
        x = a or b
        """
        expected = """
        if a:
            boolop__U0 = a
        else:
            boolop__U0 = b
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_boolop_and_and(self):
        src = """
        x = a and (b and c)
        """
        expected = """
        
        if a:
            if b:
                boolop__U1 = c
            else:
                boolop__U1 = b
            boolop__U0 = boolop__U1
        else:
            boolop__U0 = a
        x = boolop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_assignment(self):
        src = """
        def test():
            x = lambda:None
        """
        expected = """
        def test():
            def lambda__U0():
                return None
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_arg(self):
        src = """
        def test():
            x = lambda a,b:a+b
        """
        expected = """
        def test():
            def lambda__U0(a,b):
                binop__U0 = a + b
                return binop__U0
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_args(self):
        src = """
        def test():
            x = lambda *a:a
        """
        expected = """
        def test():
            def lambda__U0(*a):
                return a
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_kwargs(self):
        src = """
        def test():
            x = lambda **a:a
        """
        expected = """
        def test():
            def lambda__U0(**a):
                return a
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_defaults(self):
        src = """
        def test():
            x = lambda a=1:a
        """
        expected = """
        def test():
            def lambda__U0(a=1):
                return a
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_inside_lambda(self):
        src = """
        def test():
            x = lambda:(lambda:None)
        """
        expected = """
        def test():
            def lambda__U0():
                def lambda__U1():
                    return None
                return lambda__U1
            x = lambda__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_lambda_expr(self):
        src = """
        def test():
            (lambda:None) + 1
        """
        expected = """
        def test():
            def lambda__U0():
                return None
            lambda__U0 + 1
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)

    def test_generator(self):
        src = """
        def test():
            x = (a for a in b)
        """
        expected = """
        def test():
            def generator__U0():
                for a in b:
                    yield a
            x = generator__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_lambda(self):
        src = """
        def test():
            x = (lambda:a for a in b)
        """
        expected = """
        def test():
            def generator__U0():
                for a in b:
                    def lambda__U0():
                        return a
                    yield lambda__U0
            x = generator__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_expression(self):
        src = """
        def test():
            x = (str(a) for a in b)
        """
        expected = """
        def test():
            def generator__U0():
                for a in b:
                    call__U0 = str(a)
                    yield call__U0
            x = generator__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_condition(self):
        src = """
        def test():
            x = (str(a) for a in b if a)
        """
        expected = """
        def test():
            def generator__U0():
                for a in b:
                    if a:
                        call__U0 = str(a)
                        yield call__U0
            x = generator__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_doublecondition(self):
        src = """
        def test():
            x = (str(a) for a in b if a if b)
        """
        expected = """
        def test():
            def generator__U0():
                for a in b:
                    if a:
                        if b:
                            call__U0 = str(a)
                            yield call__U0
            x = generator__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_doubleloop(self):
        src = """
        def test():
            return (x for x in a for y in b)
        """
        expected = """
        def test():
            def generator__U0():
                for x in a:
                    for y in b:
                        yield x
            call__U0 = generator__U0()
            return call__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)

    def test_generator_doubleloop_ifend(self):
        src = """
        def test():
            return (x for x in a for y in b if y)
        """
        expected = """
        def test():
            def generator__U0():
                for x in a:
                    for y in b:
                        if y:
                           yield x
            call__U0 = generator__U0()
            return call__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_generator_doubleloop_ifmiddle(self):
        src = """
        def test():
            return (x for x in a if x for y in b)
        """
        expected = """
        def test():
            def generator__U0():
                for x in a:
                    if x:
                        for y in b:
                            yield x
            call__U0 = generator__U0()
            return call__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_ifexp(self):
        src = """
        x = a if b else c
        """
        expected = """
        if b:
            ifexp__U0 = a
        else:
            ifexp__U0 = c
        x = ifexp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_ifexp2(self):
        src = """
        x = a if b+c else d
        """
        expected = """
        binop__U0 = b + c
        if binop__U0:
            ifexp__U0 = a
        else:
            ifexp__U0 = d
        x = ifexp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_ifexp3(self):
        src = """
        x = a+b if c else d
        """
        expected = """
        if c:
            ifexp__U0 = a + b
        else:
            ifexp__U0 = d
        x = ifexp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_set(self):
        src = """
        x = {a+b, c}
        """
        expected = """
        binop__U0 = a+b
        x = {binop__U0, c}
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_dict(self):
        src = """
        x = {a+b: c}
        """
        expected = """
        binop__U0 = a+b
        x = {binop__U0: c}
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
    
    
    
    
    
    
    
    
    
    
    def test_listcomp_lambda(self):
        src = """
        def test():
            x = [lambda:a for a in b]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for a in b:
                def lambda__U0():
                    return a
                list__U0 = [lambda__U0]
                listcomp__U0 += list__U0
            x = listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_listcomp_expression(self):
        src = """
        def test():
            x = [str(a) for a in b]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for a in b:
                call__U0 = str(a)
                list__U0 = [call__U0]
                listcomp__U0 += list__U0
            x = listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_listcomp_condition(self):
        src = """
        def test():
            x = [str(a) for a in b if a]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for a in b:
                if a:
                    call__U0 = str(a)
                    list__U0 = [call__U0]
                    listcomp__U0 += list__U0
            x = listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_listcomp_doublecondition(self):
        src = """
        def test():
            x = [str(a) for a in b if a if b]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for a in b:
                if a:
                    if b:
                        call__U0 = str(a)
                        list__U0 = [call__U0]
                        listcomp__U0 += list__U0
            x = listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_listcomp_doubleloop(self):
        src = """
        def test():
            return [x for x in a for y in b]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for x in a:
                for y in b:
                    list__U0 = [x]
                    listcomp__U0 += list__U0
            return listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)

    def test_listcomp_doubleloop_ifend(self):
        src = """
        def test():
            return [x for x in a for y in b if y]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for x in a:
                for y in b:
                    if y:
                        list__U0 = [x]
                        listcomp__U0 += list__U0
            return listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_listcomp_doubleloop_ifmiddle(self):
        src = """
        def test():
            return [x for x in a if x for y in b]
        """
        expected = """
        def test():
            listcomp__U0 = []
            for x in a:
                if x:
                    for y in b:
                        list__U0 = [x]
                        listcomp__U0 += list__U0
            return listcomp__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
        
    def test_compare_oneop(self):
        src = """
        test = a == b
        """
        expected = """
        test = a == b
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_compare_twoop(self):
        src = """
        test = a < b > c
        """
        expected = """
        compare__U0 = False
        test__U1 = a < b
        if test__U1:
            test__U0 = b > c
            if test__U0:
                compare__U0 = True
        test = compare__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_compare_twoop_complex(self):
        src = """
        test = a < b+c > d
        """
        expected = """
        compare__U0 = False
        binop__U0 = b+c
        test__U1 = a < binop__U0
        if test__U1:
            test__U0 = binop__U0 > d
            if test__U0:
                compare__U0 = True
        test = compare__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)

    def test_functiondef(self):
        src = """
        def f(x):
            def g(y):
                x = a * b + c
        """
        expected = """
        def f(x):
            def g(y):
                binop__U0 = a * b
                x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
        
    def test_functiondef_default(self):
        src = """
        def f(x=1+2):
            pass
        """
        expected = """
        binop__U0 = 1 + 2
        def f(x=binop__U0):
            pass
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_functiondef_primitive_default(self):
        src = """
        def f(x=1):
            pass
        """
        expected = """
        def f(x=1):
            pass
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_classdef(self):
        src = """
        class f(a + b):
                pass
        """
        expected = """
        binop__U0 = a + b
        class f(binop__U0):
            pass
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_for(self):
        src = """
        for x in l:
            x = a * b + c
        """
        expected = """
        for x in l:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_forelse(self):
        src = """
        for x in l:
            pass
        else:
            x = a * b + c
        """
        expected = """
        for x in l:
            pass
        else:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
        
    def test_for_iterator(self):
        src = """
        for x in a + b:
            pass
        """
        expected = """
        binop__U0 = a + b
        for x in binop__U0:
            pass
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_for_target(self):
        src = """
        for x.abc in l:
            a + b
        """
        expected = """
        for target__U0 in l:
            x.abc = target__U0
            a + b
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_while(self):
        src = """
        while test:
            x = a * b + c
        """
        expected = """
        while test:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_whileelse(self):
        src = """
        while test:
            pass
        else:
            x = a * b + c
        """
        expected = """
        while test:
            pass
        else:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    
    def test_while(self):
        src = """
        while a + b:
            f()
        """
        expected = """
        binop__U0 = a + b
        while binop__U0:
            f()
            binop__U0 = a + b
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_if(self):
        src = """
        if test:
            x = a * b + c
        """
        expected = """
        if test:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_inside_ifelse(self):
        src = """
        if test:
            pass
        else:
            x = a * b + c
        """
        expected = """
        if test:
            pass
        else:
            binop__U0 = a * b
            x = binop__U0 + c
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_if(self):
        src = """
        if a + b:
            pass
        """
        expected = """
        binop__U0 = a + b
        if binop__U0:
            pass
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_raise_threeargs(self):
        src = """
        raise a+b, c+d, e+f
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        binop__U2 = e + f
        raise binop__U0, binop__U1, binop__U2
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_raise_twoargs(self):
        src = """
        raise a+b, c+d
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        raise binop__U0, binop__U1
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_raise_onearg(self):
        src = """
        raise a+b
        """
        expected = """
        binop__U0 = a + b
        raise binop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_yield(self):
        src = """
        def f():
            yield a+b
        """
        expected = """
        def f():
            binop__U0 = a + b
            yield binop__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_no_args(self):
        src = """
        f()
        """
        expected = """
        f()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_func(self):
        src = """
        (a+b)()
        """
        expected = """
        binop__U0 = a + b
        binop__U0()
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_args(self):
        src = """
        f(a+b,c+d)
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        f(binop__U0, binop__U1)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_keyword(self):
        src = """
        f(a+b,x=c+d)
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        f(binop__U0, x=binop__U1)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_keywords(self):
        src = """
        f(x=a+b,y=c+d)
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        f(x=binop__U0, y=binop__U1)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_star(self):
        src = """
        f(a+b,*(c+d))
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        f(binop__U0, *binop__U1)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_call_kwargs(self):
        src = """
        f(*(a+b),**(c+d))
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        f(*binop__U0, **binop__U1)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_repr(self):
        src = """
        `a+b`
        """
        expected = """
        binop__U0 = a + b
        `binop__U0`
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_subscript(self):
        src = """
        x = a[a+b]
        """
        expected = """
        binop__U0 = a + b
        x = a[binop__U0]
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_subscript_lhs(self):
        src = """
        (a+b)[c+d] = x
        """
        expected = """
        binop__U0 = a + b
        binop__U1 = c + d
        binop__U0[binop__U1] = x
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_attr(self):
        src = """
        x = a.y
        """
        expected = """
        x = a.y
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_attr_lhr(self):
        src = """
        (a+b).y = x
        """
        expected = """
        binop__U0 = a + b
        binop__U0.y = x
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_tuple_nested(self):
        src = """
        (a,(b,c),d) = x
        """
        expected = """
        a,tuple__U0,d = x
        b,c = tuple__U0
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_tuple_nested2(self):
        src = """
        (a,(b,c[1+2]),d) = x
        """
        expected = """
        a,tuple__U0,d = x
        b,tuple__U1 = tuple__U0
        binop__U0 = 1 + 2
        c[binop__U0] = tuple__U1
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
        
    def test_list(self):
        src = """
        x = [1,2+3,4]
        """
        expected = """
        binop__U0 = 2 + 3
        x = [1, binop__U0, 4]
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    def test_tuple(self):
        src = """
        x = (1,2+3,4)
        """
        expected = """
        binop__U0 = 2 + 3
        x = (1, binop__U0, 4)
        """
        utils.compare(src, expected, decomplexexpr.DeComplexExpr)
        
    