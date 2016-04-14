'''
Created on Oct 22, 2014

@author: stefan
'''

import ast
import scoping
from pydron.translation.astwriter import mk_assign, mk_name, mk_call
from pydron.translation import transformer

class DeUnbound(transformer.AbstractTransformer):
    """
    Makes sure that all variables are bound by ensuring that they are
    assigned to a special value `__pydron_unbound__` when they would
    otherwise be unbound.
    
    Wraps accesses with  `__pydron_unbound_check__(x)`
    that throws the `UnboundLocalError` if required.
    
    If an access is wrapped with `__pydron_unbound_unchecked__(x)`
    then the access won't be checked, The wrapping call is removed.
    
    Requires scope information (regular or extended)
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = {'lambda'}
    
    #: List of features that are removed from the AST.
    removed_features = {'deletevar'}
    
    #: List of features added to the AST.
    added_features = {'complexexpr' , 'overwrite'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
    
    def visit_FunctionDef(self, node):
        
        parameters = [arg.id for arg in node.args.args]
        if node.args.vararg:
            parameters.append(node.args.vararg)
        if node.args.kwarg:
            parameters.append(node.args.kwarg)
        
        return self._visit_block(node, set(parameters))
    
    def visit_ClassDef(self, node):
        return self._visit_block(node, set())
    
    def _visit_block(self, node, parameters):
        node = self.generic_visit(node)
        # initialize only variables that are not initialized at this point.
        localvars = set([var for var,scope in node.scopes.iteritems() if scope == scoping.Scope.LOCAL or scope == scoping.Scope.SHARED])
        localvars -= parameters
        
        localvars = [v for v in localvars if not v.startswith("__pydron")]
        
        assignments = [mk_assign(var, mk_name('__pydron_unbound__')) for var in localvars]
        node.body = assignments + node.body
        return node
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and (
                    node.func.id == "__pydron_unbound_check__" or 
                    node.func.id == "__pydron_unbound_unchecked__"):
            return node
        else:
            return self.generic_visit(node)
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and not node.id.startswith("__pydron") and not node.id == "True" and not node.id == "False" and not node.id == "None":
            return mk_call('__pydron_unbound_check__', [node])
        else:
            return node

    def visit_Delete(self, node):
        statements = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                statements.append(mk_assign(target.id, mk_name('__pydron_unbound__')))
            else:
                statements.append(ast.Delete(targets=[target]))
        return statements
    
    