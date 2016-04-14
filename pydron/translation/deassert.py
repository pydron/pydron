# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation import transformer
from pydron.translation.astwriter import mk_call, mk_name, mk_not

class DeAssert(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'assert'}
    
    #: List of features added to the AST.
    added_features = {'raise', 'complexexpr'}
    
    def __init__(self, id_factory):
        pass
    
    def visit_Assert(self, node):
        node = self.generic_visit(node)
        
        if node.msg:
            inst = mk_call("AssertionError", [node.msg])
            raise_stmt = ast.Raise(type=inst, inst=None, tback=None)
        else:
            raise_stmt = ast.Raise(type=mk_name("AssertionError"), inst=None, tback=None)
            
        check = ast.If(test=mk_not(node.test), body=[raise_stmt], orelse=[])
        return ast.If(test=mk_name("__debug__"), body=[check], orelse=[])
    