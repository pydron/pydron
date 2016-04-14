# Copyright (C) 2014 Stefan C. Mueller

from pydron.translation.astwriter import mk_assign, mk_name, mk_call_expr
from pydron.translation import transformer

class DeDecorator(transformer.AbstractTransformer):
    """
    Removes decorators from functions and classes by
    making the function calls explicit.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'decorator'}
    
    #: List of features added to the AST.
    added_features = {'complexexpr'}
    
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
    
    def visit_FunctionDef(self, node):
        node = self.generic_visit(node)
        return self._dedecorate(node)
        
    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self._dedecorate(node)
    
    def _dedecorate(self, node):
        if not node.decorator_list:
            return node
        
        # use a temporary name
        orig_id = node.name
        node.name = self.id_factory(orig_id)
        
        # call the decorators
        obj = mk_name(node.name)
        for decorator_expr in reversed(node.decorator_list):
            obj = mk_call_expr(decorator_expr, [obj])
            
        # assign to the original name
        assignment_stmt = mk_assign(orig_id, obj)
        
        node.decorator_list = []
        
        return [node, assignment_stmt]
    