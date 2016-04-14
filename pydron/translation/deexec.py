# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_call, mk_name
from pydron.translation import transformer

class DeExec(transformer.AbstractTransformer):
    """
    Removes default arguments of functions (but not lambdas).
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'exec'}
    
    #: List of features added to the AST.
    added_features =  {'locals', 'complexexpr', 'global'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
    
    def visit_Exec(self, node):
        if not node.locals and not node.globals:
            l = mk_call("locals")
            g = mk_call("globals")
        else:
            l = node.locals
            g = node.globals
        if l is None:
            l = mk_name("None")
        if g is None:
            g = mk_name("None")
        return ast.Expr(value=mk_call("__pydron_exec__", args=[node.body, l, g]))
