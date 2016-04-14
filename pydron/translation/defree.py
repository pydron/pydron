'''
Created on Oct 15, 2014

@author: stefan
'''


import ast
import scoping
from pydron.translation import naming
from pydron.translation.astwriter import mk_call, mk_str, mk_name, mk_tuple, mk_assign
from pydron.translation import transformer

class DeFree(transformer.AbstractTransformer):
    """
    Each variable which is either SHARED or FREE is represented by a cell object.
    
    For each shared variable a cell is created at the beginning of the block, and assigned
    to the variable.
    
    For each free variable a parameter is added to the block. This makes the free variable
    local.
    
    Each function with such cell parameters is wrapped in a callable object which 
    injects the cell arguments when invoked.
    
    Each access to a free or shared variable `x` is rewritten to `x.cell_contents`.
    
    ClassDef bodies cannot access free variables, nor can local variables be shared. It can
    be, however, that shared variables from a function enclosing the class are used as
    free variables in functions encoded by the class. For such variables we assume
    a corresponding `naming.passthrough_var` variable in the class body.
    We generate code that reads this variable, but no code that assigns them. To account
    for this, we introduce the feature `unassigned_passthrough`.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = {'lambda'}
    
    #: List of features that are removed from the AST.
    removed_features = {'closure_func'}
    
    #: List of features added to the AST.
    added_features =  {'unassigned_passthrough', 'complexexpr', 'overwrite'}
    
    
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
        
    def visit_FunctionDef(self, node):
        
        self.generic_visit(node)
               
        scopes = node.scopes
        shared = [var for var,scope in scopes.iteritems() if scope == scoping.Scope.SHARED]
        free = [var for var,scope in scopes.iteritems() if scope == scoping.Scope.FREE]
        
        # create cells first thing in body
        shared_stmts = [mk_assign(var, mk_call("__pydron_new_cell__", [mk_str(var)])) for var in shared]
        
        fixed_arguments = []
        for arg in node.args.args:
            if isinstance(arg, ast.Attribute) and arg.attr == "cell_contents":
                # the generic_visit above made a mess. The attribute is
                # a free/shared variable and visit_Name replaced it with
                # an attribute. This makes no sense, so lets repair the damage.
                #
                # We don't want to change the parameter name. And I don't
                # want to change the variable name either. To solve this
                # we temporarily assign it to another variable:
                #
                # def foo(freevar):
                #    freevar__U0 = freevar
                #    freevar = __pydron_new_cell__('freevar')
                #    freevar.cell_contents = freevar__U0
                
                varname = arg.value.id
                
                tmp = self.id_factory(varname)
                
                # freevar__U0 = freevar
                shared_stmts.insert(0, mk_assign(tmp, mk_name(varname)))
                
                # freevar = __pydron_new_cell__('freevar')
                # is already in shared_stmts
                
                # reevar.cell_contents = freevar__U0
                arg.ctx = ast.Store()
                shared_stmts.append(ast.Assign(targets=[arg], value=mk_name(tmp)))
                
                fixed_arguments.append(ast.Name(id=varname, ctx=ast.Param()))
            else:
                fixed_arguments.append(arg)
        node.args.args = fixed_arguments
                
        node.body = shared_stmts + node.body
        
        if free:
            # free vars become arguments
            free_args = [ast.Name(id=var, ctx=ast.Param()) for var in free]
            node.args.args = free_args + node.args.args
            
            # rename the function
            orig_name = node.name
            tmp_name = self.id_factory(node.name)
            node.name = tmp_name
            
            # wrap it
            if self._inside_class():
                wrap_args = [mk_name(naming.passthrough_var(var)) for var in free]
            else:
                wrap_args = [mk_name(var) for var in free]
            wrap_call = mk_call("__pydron_wrap_closure__", [mk_name(tmp_name), mk_tuple(wrap_args)])
            wrap_stmt = mk_assign(orig_name, wrap_call)
            
            
            return [node, wrap_stmt]
    
        else:
            return node
            
    def visit_Name(self, node):
        if node.id_scope != scoping.Scope.FREE and node.id_scope != scoping.Scope.SHARED:
            return node
        
        expr = ast.Attribute()
        expr.value = mk_name(node.id)
        expr.attr = "cell_contents"
        expr.ctx = node.ctx
        return expr