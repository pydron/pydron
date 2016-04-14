'''
Created on Oct 14, 2014

@author: stefan
'''



import ast
import enum

class Scope(enum.Enum):
    """
    Name-binding scope of an identifier.
    """
    
    #: Variable local to the block.
    #: With extended scope information, local variables
    #: which are also accessed from nested scopes (closures)
    #: are given a `SHARED` scope.
    LOCAL = "LOCAL"
    
    #: Variable local to the block which are used from a
    #: nested scope (closure). Without extended scope
    #: information this variables are reported as `LOCAL`
    #: instead.
    SHARED = "SHARED"
    
    #: Variables in the module. Variables that are used
    #: directly in the module, and there therefore both
    #: global and local, are given `GLOBAL` scope.
    GLOBAL = "GLOBAL"
    
    #: Variable belongs to en enclosing block.
    #: With extended scope information this also includes
    #: variables that aren't directly used in the current
    #: block but are used in enclosed blocks and belong
    #> an enclosing block.
    FREE = "FREE"
    
class ScopeRemover(ast.NodeVisitor):
    """
    Removes all scope information.
    """
    
    def __init__(self):
        self.fields = {}
        for asttype, field in ScopeAssigner._scoped_fields:
            fields = self.fields.get(asttype, [])
            fields.append(field)
            self.fields[asttype] = field
    
    def visit(self, node):
        if hasattr(node, "scopes"):
            del node.scopes
        for field in self.fieldsget(type(node), []):
            delattr(node, field + "_scope")
        
        

class LocalVariableCollector(ast.NodeVisitor):
    """
    Scans the code of a block (module, class, or function) and
    collects which variables are assigned and which are explicitly
    declared as global.
    
    This visitor does NOT go into nested blocks.
    """
    
    def __init__(self):
        
        #: Variables that are read directly within the visited node
        self.read_vars = set()
        
        #: Variables assigned directly within the visited node.
        self.assigned_vars = set()
        
        #: Variables explicitly declared as global within the visited node.
        self.global_vars = set()
        
        self._inside = False
        self._default_values_count = False
    
    def visit_Module(self, node):
        self._visit_block(node)
    
    def visit_ClassDef(self, node):
        self._visit_block_with_decorators_or_args(node)
    
    def visit_FunctionDef(self, node):
        self._visit_block_with_decorators_or_args(node)
        
    def visit_Lambda(self, node):
        self._visit_block(node)
        
    def visit_GeneratorExp(self, node):
        self._visit_block(node)
        
    def _visit_block(self, node):
        if not self._inside:
            self._inside = True
            self.generic_visit(node)
            self._inside = False
            return True
        else:
            return False
        
    def _visit_block_with_decorators_or_args(self, node):
        if not self._inside:
            self._inside = True
            self.generic_visit(node)
            self._inside = False
            return True
        else:
            # decorators are outside the function
            for decorator in node.decorator_list:
                self.visit(decorator)
            self.assigned_vars.add(node.name)
            
            if hasattr(node, "args"):
                self._default_values_count = True
                self.visit(node.args)
                self._default_values_count = False
        
    def visit_arguments(self, node):
        
        if self._default_values_count:
            for default in node.defaults:
                self.visit(default)
        else:
            if node.vararg:
                self.assigned_vars.add(node.vararg)
            if node.kwarg:
                self.assigned_vars.add(node.kwarg)
            for arg in node.args:
                self.visit(arg)

    def visit_alias(self, node):
        if node.asname:
            self.assigned_vars.add(node.asname)
        else:
            self.assigned_vars.add(node.name.split(".")[0])
    
    def visit_Name(self, node):
        assigned = isinstance(node.ctx,ast.Store) or isinstance(node.ctx,ast.Param) or isinstance(node.ctx,ast.Del)
        if assigned:
            self.assigned_vars.add(node.id)
        else:
            self.read_vars.add(node.id)
    
    def visit_Global(self, node):
        for identifer in node.names:
            self.global_vars.add(identifer)


class ScopeAssigner(ast.NodeVisitor):
    """
    Visitor that assigns the scope to each identifier that represents a name.
    
    Those are:
    
    * `ast.FunctionDef.name`
    * `ast.ClassDef.name`
    * `ast.Global.names`
    * `ast.Name.id`
    * `ast.arguments.vararg` and `ast.arguments.kwarg`
    * either `ast.alias.name` or `ast.alias.asname`
    
    For each of them an attribute with a `_scope` prefix is set. For example
    `ast.Name.id_scope`. The attribute is set to an instance of `Scope`, or
    a list thereof.
    
    Each node that represents a block (Module, ClassDef, FunctionDef, 
    Lambda, and Generator) is assigned a `scopes` attribute that contains
    a `variable->scope` `dict` for all variables used directly in that block.
    """
    
    #: Fields of the AST classes that contain identifiers that have a scope.
    #: The list excludes `ast.alias` which has to be handled separately.
    _scoped_fields = set([
        (ast.FunctionDef, "name"),
        (ast.ClassDef, "name"),
        (ast.Global, "names"),
        (ast.Name, "id"),
        (ast.arguments, "vararg"),
        (ast.arguments, "kwarg"),
    ])

    
    class Block(object):
        def __init__(self, enclosing_block, node, read_vars, assigned_vars, global_vars):
            self.enclosing_block = enclosing_block
            self.node = node
            self.read_vars = read_vars
            self.assigned_vars = assigned_vars
            self.global_vars = global_vars
            
            self.all = self.read_vars | self.assigned_vars | self.global_vars
            self.scopes = {v : self._scope(v) for v in self.all}
            
        def scope(self, var):
            return self.scopes[var]
            
        def _scope(self, var, nested=False):
            if isinstance(self.node, ast.ClassDef) and nested:
                if self.enclosing_block:
                    return self.enclosing_block._scope(var, nested=True)
                else:
                    return Scope.GLOBAL
            elif isinstance(self.node, ast.Module):
                return Scope.GLOBAL
            else:                    
                if var in self.global_vars:
                    return  Scope.GLOBAL
                elif var in self.assigned_vars:
                    if nested:
                        return Scope.FREE
                    else:
                        return Scope.LOCAL
                elif self.enclosing_block:
                    return self.enclosing_block._scope(var, nested=True)
                else:
                    return  Scope.GLOBAL
        
    def __init__(self):
        self.current_block = None
        
    def visit(self, node):
        for field in node._fields:
            if (node.__class__, field) in self._scoped_fields:
                self._store_scope(node, field)
        return ast.NodeVisitor.visit(self, node)
        
    def visit_Module(self, node):
        self._visit_block(node)
    
    def visit_ClassDef(self, node):
        self._visit_block_with_complications(node)
        
    def visit_FunctionDef(self, node):
        self._visit_block_with_complications(node)
        
    def visit_Lambda(self, node):
        self._visit_block_with_complications(node)
        
    def visit_GeneratorExp(self, node):
        self._visit_block(node)
        
    def visit_alias(self, node):
        if node.asname:
            node.asname_scope = self._get_scope(node.asname)
        else:
            identifier = node.name.split(".")[0]
            node.name_scope = self._get_scope(identifier)
        
    def _get_scope(self, identifier):
        if self.current_block:
            return self.current_block.scope(identifier)
        else:
            return Scope.GLOBAL
        
    def _store_scope(self, node, field):
        value = getattr(node, field)
        if value is not None:
            if isinstance(value, list):
                scope = [self._get_scope(identifier) for identifier in value]
            else:
                scope = self._get_scope(value)
            setattr(node, field + "_scope", scope)
        
    def _visit_block_with_complications(self, node):
        # decorators are outside the function
        if hasattr(node, "decorator_list"):
            decorators = node.decorator_list
            for d in decorators:
                self.visit(d)
        
            # little trick to avoid traversing
            # the decorators while we are inside
            node.decorator_list = []
            
        # default values are too
        if hasattr(node, "args"):
            defaults = node.args.defaults
            for d in defaults:
                self.visit(d)
            node.args.defaults = []
            
        self._visit_block(node)
        
        if hasattr(node, "args"):
            node.args.defaults = defaults
        if hasattr(node, "decorator_list"):
            node.decorator_list = decorators
        
    def _visit_block(self, node):
        prescan = LocalVariableCollector()
        prescan.visit(node)
        self.current_block = self.Block(self.current_block,
                                        node,
                                        prescan.read_vars,
                                        prescan.assigned_vars,
                                        prescan.global_vars)
        self.generic_visit(node)
        node.scopes = self.current_block.scopes
        self.current_block = self.current_block.enclosing_block

    
            
class ExtendedScopeAssigner(ast.NodeVisitor):
    """
    TODO document subblocks_free
    """
    
    class Phase1(ast.NodeVisitor):
                
        def __init__(self):
            self._freevars_stack = [set()]
        
        def visit_Module(self, node):
            self._visit_block(node)
        
        def visit_ClassDef(self, node):
            self._visit_block(node, isfunction = False)
            
        def visit_FunctionDef(self, node):
            self._visit_block(node)
            
        def visit_Lambda(self, node):
            self._visit_block(node)
            
        def visit_GeneratorExp(self, node):
            self._visit_block(node)
            
        def _visit_block(self, node, isfunction=True):
            
            self._freevars_stack.append(set())
            self.generic_visit(node)
            subblocks_free = self._freevars_stack.pop()
            
            # our own variables
            block_free = set(var for var,scope in node.scopes.iteritems() if scope == Scope.FREE)
            block_local = set(var for var,scope in node.scopes.iteritems() if scope == Scope.LOCAL)
            block_global = set(var for var,scope in node.scopes.iteritems() if scope == Scope.GLOBAL)
            
            assert not (subblocks_free & block_global), "A free variable of a sub-block should not be global in the parent"
            
            if isfunction:
            
                # Add vars to block_free that are are just passing through.
                block_free |= subblocks_free - block_local
                
                # Local variables used as free variables by a subblock
                block_shared = subblocks_free & block_local
         
                # Purely local variables that are not used in closures
                block_local -= block_shared
        
                scopes = {}
                scopes.update({var : Scope.LOCAL for var in block_local})
                scopes.update({var : Scope.SHARED for var in block_shared})
                scopes.update({var : Scope.FREE for var in block_free})
                scopes.update({var : Scope.GLOBAL for var in block_global})
                node.scopes = scopes
                self._freevars_stack[-1].update(block_free)
                
            else:
                
                # Variables local to the class scope are not free variables
                # of sub-blocks.
                self._freevars_stack[-1].update(block_free | subblocks_free)
            
    class Phase2(ast.NodeVisitor):
        
        def __init__(self):
            self._scope_stack = []
            
        def visit(self, node):
            if not isinstance(node, ast.alias):
                for field in node._fields:
                    if hasattr(node, field + "_scope"):
                        self._set_scope(node, field)
            return ast.NodeVisitor.visit(self, node)
        
        def visit_alias(self, node):
            if node.asname:
                node.asname_scope = self._get_scope(node.asname)
            else:
                node.name_scope = self._get_scope(node.name.split(".")[0])
        
        def _set_scope(self, node, field):
            value = getattr(node, field)
            if value is not None:
                if isinstance(value, list):
                    scope = [self._get_scope(identifier) for identifier in value]
                else:
                    scope = self._get_scope(value)
                setattr(node, field + "_scope", scope)
                
        def _get_scope(self, identifier):
            if self._scope_stack:
                return self._scope_stack[-1][identifier]
            else:
                return Scope.GLOBAL
    
        def visit_Module(self, node):
            self._visit_block(node)
        
        def visit_ClassDef(self, node):
            self._visit_block_with_complications(node)
            
        def visit_FunctionDef(self, node):
            self._visit_block_with_complications(node)
            
        def visit_Lambda(self, node):
            self._visit_block_with_complications(node)
            
        def visit_GeneratorExp(self, node):
            self._visit_block(node)
            
            
            
        def _visit_block_with_complications(self, node):
            # decorators are outside the function
            if hasattr(node, "decorator_list"):
                decorators = node.decorator_list
                for d in decorators:
                    self.visit(d)
            
                # little trick to avoid traversing
                # the decorators while we are inside
                node.decorator_list = []
                
            # default values are too
            if hasattr(node, "args"):
                defaults = node.args.defaults
                for d in defaults:
                    self.visit(d)
                node.args.defaults = []
                
            self._visit_block(node)
            
            if hasattr(node, "args"):
                node.args.defaults = defaults
            if hasattr(node, "decorator_list"):
                node.decorator_list = decorators
            
        def _visit_block(self, node):
            self._scope_stack.append(node.scopes)
            self.generic_visit(node)
            self._scope_stack.pop()


    def visit(self, node):
        self.Phase1().visit(node)
        self.Phase2().visit(node)
        
