'''
Created on Oct 15, 2014

@author: stefan
'''

import ast


def mk_name(variable_id):
    return ast.Name(id=variable_id, ctx=ast.Load())

def mk_str(s):
    return ast.Str(s=s)

def mk_num(n):
    return ast.Num(n=n)

def mk_None():
    return mk_name("None")

def mk_add(a,b):
    return ast.BinOp(left=a, right=b, op=ast.Add())

def mk_bitor(a,b):
    return ast.BinOp(left=a, right=b, op=ast.BitOr())

def mk_not(x):
    return ast.UnaryOp(op=ast.Not(), operand=x)

def mk_assign(target_id, value_expr):
    """
    Returns a statement for `target_id = value_expr`
    """
    name = ast.Name(id=target_id, ctx=ast.Store())
    return ast.Assign(targets=[name], value=value_expr)

def mk_call(func_id, args=[], keywords=[], vararg=None, kwarg=None):
    return mk_call_expr(mk_name(func_id), args, keywords, vararg, kwarg)

def mk_call_expr(func_expr, args=[], keywords=[], vararg=None, kwarg=None):
    return ast.Call(func=func_expr, args=list(args), keywords=list(keywords), starargs=vararg, kwargs = kwarg)

def mk_tuple(elements):
    return ast.Tuple(elts=list(elements), ctx=ast.Load())

def mk_list(elements):
    return ast.List(elts=list(elements), ctx=ast.Load())

def mk_set(elements):
    return ast.Set(elts=list(elements))

def mk_attr(obj_expr, attribute):
    return ast.Attribute(value=obj_expr, attr=attribute, ctx=ast.Load())

def mk_attr_assign(obj_expr, attribute, value_expr):
    attr_expr = ast.Attribute(value=obj_expr, attr=attribute, ctx=ast.Store())
    return ast.Assign(targets=[attr_expr], value=value_expr)

def mk_subscript_assign(obj_expr, index_expr, value_expr):
    subscript_expr = ast.Subscript(value=obj_expr, slice=ast.Index(value=index_expr), ctx=ast.Store())
    return ast.Assign(targets=[subscript_expr], value=value_expr)

def mk_dict(key_value_list):
    key_value_list = list(key_value_list)
    keys = [k for k,_ in key_value_list]
    values = [v for _,v in key_value_list]
    return ast.Dict(keys=keys, values=values)