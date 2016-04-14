# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_call, mk_tuple, mk_name
from pydron.translation import transformer

class DePrint(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'print'}
    
    #: List of features added to the AST.
    added_features = {'complexexpr'}
    
    def __init__(self, id_factory):
        pass
    
    def visit_Print(self, node):
        node = self.generic_visit(node)
        
        if node.dest:
            dest = node.dest
        else:
            dest = mk_name("None")
            
        if node.nl:
            nl = mk_name("True")
        else:
            nl = mk_name("False")
        
        values = mk_tuple(node.values) 
        call = mk_call("__pydron_print__", [dest, values, nl])
        return ast.Expr(value=call)

    