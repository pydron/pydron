'''
Created on Oct 15, 2014

@author: stefan
'''


import ast
import scoping
from pydron.translation.astwriter import mk_call, mk_str, mk_name
from pydron.translation import transformer

class DeGlobal(transformer.AbstractTransformer):
    """
    Transforms the AST so that there are no more global variables.
    
    Every read access to a global variable is replaced
    with `__pydron_read_global__('variablename')`.
    Every assignment is replaced with `__pydron_read_global__('variablename', value)`
    
    Technically speaking, both `__pydron_read_global__` and `__pydron_read_global__` 
    are global variables. But we have special rules for them when translating the
    AST to the graph, so this is fine. Also, both are only used as functions.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = {'multitarget'}
    
    #: List of features that are removed from the AST.
    removed_features = {'global'}
    
    #: List of features added to the AST.
    added_features =  {'complexexpr'}

    def __init__(self, id_factory):
        self.id_factory = id_factory
        self.stack = []
    
    def visit_Module(self, node):
        self.stack.append(node)
        self.generic_visit(node)
        self.stack.pop()
        return node
        
    def inside_module(self):
        return isinstance(self.stack[-1], ast.Module)
        
    def visit_Global(self, node):
        return None # Remove statement
    
    def visit_Name(self, node):
        if self.inside_module():
            return node
        
        if not self.is_global_name(node):
            return node
        if isinstance(node.ctx, ast.Load):
            return mk_call("__pydron_read_global__", args=[mk_str(node.id)])
        else:
            raise ValueError("Unhandled assignment to a global variable: %s." % node.id)
        
    def visit_Assign(self, node):
        node.value = self.generic_visit(node.value)
        
        if self.inside_module():
            return node
        
        statements = []
        
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and self.is_global_name(target):
                stmt = mk_call("__pydron_assign_global__", args=[mk_str(target.id), node.value])
                statements.append(ast.Expr(value=stmt))
            else:
                statements.append(node)
        else:
            raise ValueError("not supported")
        
        return statements
    
    def visit_Delete(self, node):
        
        if self.inside_module():
            return node
        
        statements = []
        for target in node.targets:
            if isinstance(target, ast.Name) and self.is_global_name(target):
                stmt = mk_call("__pydron_delete_global__", args=[mk_str(target.id)])
                statements.append(ast.Expr(stmt))
            else:
                statements.append(ast.Delete(targets=[target]))
        return statements
        
    def visit_FunctionDef(self, node):
        self.stack.append(node)
        node = self.generic_visit(node)
        self.stack.pop()
        
        if self.inside_module():
            return node
                
        if self.is_global(node, "name"):
            orig_name = node.name
            new_name = self.id_factory(orig_name)
            node.name = new_name
            stmt = mk_call("__pydron_assign_global__", args=[mk_str(orig_name), mk_name(new_name)])
            return [node, ast.Expr(stmt)]
        else:
            return node
        
    def visit_ClassDef(self, node):
        self.stack.append(node)
        node = self.generic_visit(node)
        self.stack.pop()
        
        if self.inside_module():
            return node
        
        if self.is_global(node, "name"):
            orig_name = node.name
            new_name = self.id_factory(orig_name)
            node.name = new_name
            stmt = mk_call("__pydron_assign_global__", args=[mk_str(orig_name), mk_name(new_name)])
            return [node, ast.Expr(stmt)]
        else:
            return node
        
    def visit_Lambda(self, node):
        self.stack.append(node)
        node = self.generic_visit(node)
        self.stack.pop()
        
    def visit_ExceptHandler(self, node):
    
        if self.inside_module():
            return node
        
        if isinstance(node.name, ast.Name) and self.is_global_name(node.name):
            var = node.name.id
            stmt = mk_call("__pydron_assign_global__", args=[mk_str(var), mk_name(var)])
            node.body = [ast.Expr(stmt)] + node.body
        elif node.name:
            node.name = self.visit(node.name)
        
        if node.type:
            node.type = self.visit(node.type)
            
        return node
    
    def is_global_name(self, name):
        return self.is_global(name, "id")
    
    def is_global(self, node, field):
        name = getattr(node, field)
        scope = getattr(node, field+"_scope")
        special = name == "True" or name == "False" or name == "None"
        return scope == scoping.Scope.GLOBAL and not name.startswith('__pydron') and not special