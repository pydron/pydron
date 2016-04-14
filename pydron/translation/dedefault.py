# Copyright (C) 2014 Stefan C. Mueller

from pydron.translation.astwriter import mk_str, mk_tuple, mk_name, mk_call, mk_assign
from pydron.translation import transformer

class DeDefault(transformer.AbstractTransformer):
    """
    Removes default arguments of functions (but not lambdas).
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'funcdefaultvalues'}
    
    #: List of features added to the AST.
    added_features =  set()
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
        
    def visit_FunctionDef(self, node):
        args = node.args
        
        if not args.defaults:
            return node
        
        orig_id = node.name
        node.name = self.id_factory(orig_id)
        
        parameters = mk_tuple(mk_str(arg.id) for arg in args.args)
        defaults = mk_tuple(args.defaults)
        
        parameters_id = self.id_factory("tuple")
        parameters_stmt = mk_assign(parameters_id, parameters)
        parameters = mk_name(parameters_id)
        
        defaults_id = self.id_factory("tuple")
        default_stmt = mk_assign(defaults_id, defaults)
        defaults = mk_name(defaults_id)
        
        args.defaults = []
        
        func_expr = mk_call("__pydron_defaults__", [mk_name(node.name), parameters, defaults])
        assign_stmt = mk_assign(orig_id, func_expr)
        
        return [node, parameters_stmt, default_stmt, assign_stmt]
    