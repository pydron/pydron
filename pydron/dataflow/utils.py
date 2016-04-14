# Copyright (C) 2015 Stefan C. Mueller

import ast

def contains_sideeffects(g):
    """
    Checks if the graph contains at least one task with
    a task property `syncpoint` which is `True`.
    
    It also checks subgraphs stored within tasks, given
    that the task objects have a `subgraphs()` method.
    """
    
    visited_graphs = set()
    
    def visit(g):
        
        # avoid infinite loops if subgraphs are cyclic.
        if id(g) in visited_graphs:
            return False
        visited_graphs.add(id(g))
        
        for tick in g.get_all_ticks():
            if g.get_task_properties(tick).get('syncpoint', False):
                return True
            
            task = g.get_task(tick)
            for subgraph in task.subgraphs():
                if visit(subgraph):
                    return True
        return False
    return visit(g)
    

def assert_graph_equal(expected, actual):
    
    def trim(lines):
        for line in lines:
            line = line.strip()
            if line:
                yield line
                
                
    if expected != actual:
        expected_clean = "\n".join(trim(repr(expected).splitlines()))
        actual_clean = "\n".join(trim(repr(actual).splitlines()))
    
        
        for i, (e, a) in enumerate(zip(expected_clean.splitlines(), actual_clean.splitlines())):
            if e != a:
                msg = "Difference on line %s: Expected %s got %s" % (i, repr(e), repr(a))
                break
        else:
            msg = "No difference in string representation."
        
        print repr(expected)
        print repr(actual)
        raise AssertionError("Graphs differ: %s" % msg)


def binop(left, right, op):
    if op == ast.Add:
        value = left + right
    elif op == ast.Sub:
        value = left - right
    elif op == ast.Mult:
        value = left * right
    elif op == ast.Div:
        value = left / right
    elif op == ast.Mod:
        value = left % right
    elif op == ast.Pow:
        value = left ** right
    elif op == ast.LShift:
        value = left << right
    elif op == ast.RShift:
        value = left >> right
    elif op == ast.BitOr:
        value = left | right
    elif op == ast.BitXor:
        value = left ^ right
    elif op == ast.BitAnd:
        value = left & right
    elif op == ast.FloorDiv:
        value = left // right
        
    elif op == ast.Eq:
        value = left == right
    elif op == ast.NotEq:
        value = left != right
    elif op == ast.Lt:
        value = left < right
    elif op == ast.LtE:
        value = left <= right
    elif op == ast.Gt:
        value = left > right
    elif op == ast.GtE:
        value = left >= right
    elif op == ast.Is:
        value = left is right
    elif op == ast.IsNot:
        value = left is not right
    elif op == ast.In:
        value = left in right
    elif op == ast.NotIn:
        value = left not in right
    else:
        raise TypeError("unsupported operator")
    return value

def unaryop(value, op):
    if op == ast.Invert:
        retval = ~value
    elif op == ast.Not:
        retval =  not value
    elif op == ast.UAdd:
        retval =  +value
    elif op == ast.USub:
        retval =  -value
    else:
        raise TypeError("unsupported operator")
    return retval

def augassign(target, value, op):
    if op == ast.Add:
        target += value
    elif op == ast.Sub:
        target -= value
    elif op == ast.Mult:
        target *= value
    elif op == ast.Div:
        target /= value
    elif op == ast.Mod:
        target %= value
    elif op == ast.Pow:
        target **= value
    elif op == ast.LShift:
        target <<= value
    elif op == ast.RShift:
        target >>= value
    elif op == ast.BitOr:
        target |= value
    elif op == ast.BitXor:
        target ^= value
    elif op == ast.BitAnd:
        target &= value
    elif op == ast.FloorDiv:
        target //= value
    else:
        raise TypeError("unsupported operator")
    return target