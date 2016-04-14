'''
Created on Oct 21, 2014

@author: stefan
'''

import ast
import scoping
import naming

from pydron.translation.astwriter import mk_call, mk_str, mk_tuple, mk_assign, mk_call_expr, mk_name
from pydron.translation import transformer

class DeClass(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = {'decorator', 'nonexplicitmembers', 'locals'}
    
    #: List of features that are removed from the AST.
    removed_features = {'closure_class', 'unassigned_passthrough', 'class'}
    
    #: List of features added to the AST.
    added_features =  {'complexexpr'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
        self.node_stack = []
        
    def visit(self, node):
        self.node_stack.append(node)
        retval = ast.NodeTransformer.visit(self, node)
        self.node_stack.pop()
        return retval
        
    def _inside_class(self):
        if len(self.node_stack) >= 2:
            return isinstance(self.node_stack[-2], ast.ClassDef)
        else:
            return False

    def visit_ClassDef(self, node):
        node = self.generic_visit(node)
        
        # free variables of the class block become parameters of the function
        scopes = getattr(node, 'scopes', {})
        free = [var for var,scope in scopes.iteritems() if scope == scoping.Scope.FREE]
        free_param = [ast.Name(id=var, ctx=ast.Param()) for var in free]
        free_args = [ast.Name(id=var, ctx=ast.Load()) for var in free]
        
        # free variables of sub-blocks. Those need name mangling to avoid
        # collisions with variables local to the class block.
        passthrough = self.find_passthrough_vars(node)
        pt_param = [ast.Name(id=naming.passthrough_var(var), ctx=ast.Param()) for var in passthrough]
        pt_args = [ast.Name(id=var, ctx=ast.Load()) for var in passthrough]
        
        # function to execute the class body and collect the attributes
        func = ast.FunctionDef()
        func.name = self.id_factory("class_" + node.name)
        func.args = ast.arguments(args=free_param + pt_param, vararg=None, kwarg=None, defaults=[])
        func.body = node.body + [ast.Return(value=mk_name('__pydron_members__')) ]
        func.decorator_list = []
        
        # replicate name mangling of `LocalizeFreeVariables`
        all_args = free_args + pt_args
        if self._inside_class():
            for arg in all_args:
                arg.id = naming.passthrough_var(arg.id)
        
        # create the class
        typefunc = mk_call('__pydron_read_global__', [mk_str('type')])
        class_expr = mk_call_expr(typefunc, [mk_str(node.name), mk_tuple(node.bases), mk_call(func.name, all_args)])
        
        for decorator in reversed(node.decorator_list):
            class_expr = mk_call_expr(decorator, [class_expr])
        
        stmt = mk_assign(node.name, class_expr)
        
        return [func, stmt]
    

    def find_passthrough_vars(self, classnode):
        """
        Find passthrough variables inside the class (not nested).
        
        We cannot just read it out of classnode.scopes because
        that is not updated was we transform nested classes.
        """
        
        class PassthroughFinder(ast.NodeVisitor):
            
            def __init__(self):
                self.found_vars = []
                self.inside = False
                
            def visit_ClassDef(self, node):
                if self.inside:
                    return
                else:
                    self.inside = True
                    self.generic_visit(node)
                    self.inside = False
    
            def visit_FunctionDef(self, node):
                return
            
            def visit_Lambda(self, node):
                return
            
            def visit_GeneratorExp(self, node):
                return
            
            def visit_Name(self, node):
                name, components = naming.decode_id(node.id)
                if "P" in components:
                    self.found_vars.append(name)
        
        finder = PassthroughFinder()
        finder.visit(classnode)
        return finder.found_vars