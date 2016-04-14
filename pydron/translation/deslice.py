# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_call, mk_tuple, mk_name
from pydron.translation import transformer

class DeSlice(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'slice'}
    
    #: List of features added to the AST.
    added_features = {'complexexpr'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
    
    def visit_Slice(self, node):
        self.generic_visit(node)
        
        # ast.Slice becomes ast.Index with a slice() call.
        
        lower = node.lower
        upper = node.upper
        step = node.step
        if not lower:
            lower = mk_name("None")
        if not upper:
            upper = mk_name("None")
        if not step:
            step = mk_name("None")
                
        s = mk_call("slice", [lower, upper, step])    
        return ast.Index(value=s)
    
    def visit_Ellipsis(self, node):
        # There is a built-in for that.
        s = mk_name("Ellipsis")
        return ast.Index(value=s)

    def visit_ExtSlice(self, node):
        self.generic_visit(node)
        
        # ast.ExtSlice becomes ast.Index with a tuple.
        
        assert all(isinstance(dim, ast.Index) for dim in node.dims)
        parts = [dim.value for dim in node.dims]
        s = mk_tuple(parts)
        return ast.Index(value=s)