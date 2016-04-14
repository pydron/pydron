# Copyright (C) 2014 Stefan C. Mueller

import ast

from pydron.translation import naming, transformer
from pydron.translation.scoping import Scope
from pydron.translation.astwriter import mk_name, mk_str, mk_dict, mk_call

class DeLocals(transformer.AbstractTransformer):
    """
    Replace calls to `locals()` with calls to `__pydron_locals__(..)`
    which takes all the local variables as arguments (some might be unbound).
    """
    
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'locals'}
    
    #: List of features added to the AST.
    added_features =  {'complexexpr'}
    
    
    def __init__(self, id_factory):
        self._stack = []
    
    def visit_FunctionDef(self, node):
        return self._visit_block(node)
    
    def visit_ClassDef(self, node):
        return self._visit_block(node)
    
    def _visit_block(self, node):
        self._stack.append(node)
        node = self.generic_visit(node)
        self._stack.pop()
        return node
    
    def visit_Call(self, node):
        node = self.generic_visit(node)
        
        if not isinstance(node.func, ast.Name):
            # only direct calls, we cannot detect them otherwise
            return node
        if node.func.id_scope != Scope.GLOBAL:
            # `locals` is a python built-in.
            return node
        if node.func.id != "locals":
            return node
        
        block = self._stack[-1]
        
        def condition(var, scope):
            if naming.decode_id(var)[1]:
                # no variables we introduced
                return False
            elif var.startswith("__pydron"):
                return False
            elif scope == Scope.LOCAL or scope == Scope.SHARED:
                # local variables are welcome
                return True
            elif not isinstance(block, ast.ClassDef):
                # free variables too...
                return scope == Scope.FREE
            else:
                # ... unless we are in a class
                return False
            
        localvars = set([var for var,scope in block.scopes.iteritems() if condition(var, scope)])
        args = mk_dict((mk_str(var), mk_call('__pydron_unbound_unchecked__', [mk_name(var)])) for var in localvars)
        
        return mk_call('__pydron_locals__', [args])
    
