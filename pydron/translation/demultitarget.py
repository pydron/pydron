# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_name, mk_assign
from pydron.translation import transformer

class DeMultiTarget(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'multitarget'}
    
    #: List of features added to the AST.
    added_features = set()
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
        
    def visit_Assign(self, node):
        if len(node.targets) <= 1:
            return node
        
        stmts = []
        if not (isinstance(node.value, ast.Name) or 
                isinstance(node.value, ast.Str) or 
                isinstance(node.value, ast.Num)):
            value_id = self.id_factory("value")
            stmts.append(mk_assign(value_id, node.value))
            value = mk_name(value_id)
        else:
            value = node.value
            
        for target in node.targets:
            s = ast.Assign(targets=[target], value=value)
            stmts.append(s)
    
        return stmts