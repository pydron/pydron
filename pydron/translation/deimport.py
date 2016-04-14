'''
Created on Oct 15, 2014

@author: stefan
'''

import ast
from pydron.translation.astwriter import mk_str, mk_num, mk_call, mk_None, mk_tuple, mk_assign, mk_attr, mk_name, mk_subscript_assign
from pydron.translation import transformer

class DeImport(transformer.AbstractTransformer):
    """
    Replaces `import` and `from .. import ..` statements with calls to `__import__`.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'import', 'importfrom'}
    
    #: List of features added to the AST.
    added_features =  {'complexexpr', 'global', 'for'}
    
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
        
    def _unique_mod_id(self):
        return self.id_factory("module")
    
    def _unique_modattr_id(self):
        return self.id_factory("module_element")
    
    def visit_Import(self, node):
        statements = []
        
        for alias in node.names:
            module_expr = self.import_call_expr(alias.name)
            identifier = alias.asname if alias.asname else alias.name
            identifier = identifier.split(".")[0]
            statement = mk_assign(identifier, module_expr)
            statements.append(statement)
            
        return statements
            
    def visit_ImportFrom(self, node):
        
        tmp_identifier = self._unique_mod_id()
        
        module_expr = self.import_call_expr(node.module, [alias.name for alias in node.names], node.level)
        statements = [mk_assign(tmp_identifier, module_expr)]
        
        if any(alias.name == "*" for alias in node.names):
            
            statements.append(self.unpack_star(tmp_identifier))
        else:
            for alias in node.names:
                asname = alias.asname if alias.asname else alias.name
                attr_expr = mk_attr(mk_name(tmp_identifier), alias.name)
                statements.append(mk_assign(asname, attr_expr))
        return statements
    
    def unpack_star(self, module_id):
        tmp = self._unique_modattr_id()
        
        dir_expr = mk_call("dir", args=[mk_name(module_id)])
        all_expr = mk_call("getattr", args=[mk_name(module_id), mk_str('__all__'), dir_expr])
        
        value_expr = mk_call("getattr", args=[mk_name(module_id), mk_name(tmp)])
        body_stmt = mk_subscript_assign(mk_call("globals"), mk_name(tmp), value_expr)
        
        return ast.For(target=mk_name(tmp), iter=all_expr, body=[body_stmt], orelse=[])
            
    def import_call_expr(self, name, fromlist=None, level=None):
        name_expr = mk_str(name) if name else mk_None()
      
        if fromlist:
            from_expr = mk_tuple(mk_str(item) for item in fromlist)
        else:
            from_expr = mk_None()
        
        args = [name_expr, mk_call("globals"), mk_None(), from_expr]
        
        if level:
            args.append(mk_num(level))
    
        return mk_call("__import__", args)
        