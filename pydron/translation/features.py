# Copyright (C) 2015 Stefan C. Mueller

import ast
from pydron.translation import scoping, naming

def make_nonexistent_check(asttype, *moretypes):
    """
    Creates a function that checks if a given AST
    contains a node with the type passed to this function.
    """
    
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Target(self, node):
            """
            This will become `visit_ASTYPE(...)`. 
            """
            self.found = True
    
    def check(node):        
        visitor = Visitor()
        for t in all_types:
            setattr(visitor, "visit_" + t.__name__, visitor.visit_Target)
        visitor.visit(node)
        return visitor.found
    
    all_types = [asttype] + list(moretypes)
    
    check.__name__ = "check_" + asttype.__name__.lower()
    return check


def check_break(node):
    """
    Returns `False` if `ast.Break` only appears inside an `ast.If`
    at the very end of a `ast.For` or `ast.While`.
    """       
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Break(self, node):
            self.found = True
        
        def visit_For(self, node):
            self.visit(node.target)
            self.visit(node.iter)
            self.visit_LoopBody(node.body)
            for n in node.orelse:
                self.visit(n)
            
        def visit_While(self, node):
            self.visit(node.test)
            self.visit_LoopBody(node.body)
            for n in node.orelse:
                self.visit(n)
    
        def visit_LoopBody(self, body):
            
            # Traverse all of the function with the exception of
            # that one conditional break.
            
            if not body:
                return
            
            # In all but the last statements 'break' may not occur.
            for node in body[:-1]:
                self.visit(node)
            
            # The break must be inside a `if`
            if not isinstance(body[-1], ast.If):
                self.visit(body[-1])
                return
                
            ifstmt = body[-1]
            self.visit(ifstmt.test)
            
            # The break must be inside an `if` without an `else`
            # part and a single statement in the body.
            if len(ifstmt.body) > 1 or ifstmt.orelse:
                self.visit(ifstmt)
                return 
            
            # That one statement inside the `if` must be a `break`.
            if not isinstance(ifstmt.body[0], ast.Break):
                self.visit(ifstmt)
                return
            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_return(node):
    """
    Returns `False` if `ast.Return` only appears at the end of
    `ast.FunctionDef`.
    """       
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Return(self, node):
            self.found = True
            
        def visit_FunctionDef(self, node):
            body = node.body
            
            # Traverse all of the function with the exception of
            # that one conditional break.
            
            if not body:
                return
            
            # In all but the last statements 'return' may not occur.
            for node in body[:-1]:
                self.visit(node)
                
            if not isinstance(body[-1], ast.Return):
                self.visit(body[-1])
        
            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found

def check_funcdefaultvalues(node):
    """
    Returns if there are function definitions with default values.
    """       
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
            
        def visit_FunctionDef(self, node):
            self.generic_visit(node)
            if node.args.defaults:
                self.found = True

            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_nonexplicitmembers(node):
    """
    AST has this feature if there are classes where the members are NOT explicitly
    assigned to `__pydron_members__`.
    """       
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False

        def visit_ClassDef(self, node):
            self.generic_visit(node)
            body = node.body
            
            # Traverse all of the function with the exception of
            # that one conditional break.
            
            if not body:
                self.found = True
                return
            
            assignment = body[-1]
            if not isinstance(assignment, ast.Assign):
                self.found = True
                return
        
            if len(assignment.targets) != 1:
                self.found = True
                return
            
            target = assignment.targets[0]
            
            if not isinstance(target, ast.Name):
                self.found = True
                return
            
            if target.id != '__pydron_members__':
                self.found = True
                return
        
            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_locals(node):
    """
    Checks if there is a call to `locals()`.
    The check is not perfect has there might be local or global
    variables with that name.
    """       
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name):
                if node.func.id == "locals":
                    self.found = True

            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_decorator(node):
    """
    Check if there are decorators.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_ClassDef(self, node):
            self.generic_visit(node)
            if node.decorator_list:
                self.found = True
        
        def visit_FunctionDef(self, node):
            self.generic_visit(node)
            if node.decorator_list:
                self.found = True

            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_complexexpr(node):
    """
    Checks if there are expressions containing expressions other
    than `ast.Name`, `ast.Num`, and `ast.Str`.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
            self.stack = []
        
        def visit(self, node):
            
            if isinstance(node, ast.Name):
                return
            if isinstance(node, ast.Str):
                return
            if isinstance(node, ast.Num):
                return

            if isinstance(node, ast.expr):
                for n in reversed(self.stack):
                    if isinstance(n, ast.expr):
                        self.found = True
                    if isinstance(n, ast.stmt):
                        if isinstance(n, ast.Assign):
                            break
                        if isinstance(n, ast.Expr):
                            break
                        if isinstance(n, ast.Delete) and isinstance(node, ast.Subscript):
                            break
                        if isinstance(n, ast.Delete) and isinstance(node, ast.Attribute):
                            break
                            
                        self.found = True
     
            
            self.stack.append(node)
            
            self.generic_visit(node)
             
            if node != self.stack.pop():
                raise ValueError("stack corrupt")

            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_multitarget(node):
    """
    Check if there are assignments with multiple targets.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Assign(self, node):
            if len(node.targets) > 1:
                self.found = True

            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found

def make_closure_check(func_or_class):
    
    def check_closure_func(node, func_or_class):
        """
        Check if there are free variables.
        """
        class Visitor(ast.NodeVisitor):
            
            def __init__(self):
                self.found = False

            def visit(self, node):
                if hasattr(node, "scopes"):
                    scopes = node.scopes
                    for _, scope in scopes.iteritems():
                        if scope == scoping.Scope.FREE:
                            
                            inside_class = isinstance(node, ast.ClassDef)
                            
                            if func_or_class == "class" and inside_class:
                                self.found = True
                            if func_or_class == "func" and not inside_class:
                                self.found = True
                                
                ast.NodeVisitor.visit(self, node)
                
        visitor = Visitor()
        visitor.visit(node)
        return visitor.found

    return lambda node:check_closure_func(node, func_or_class)

def check_unassigned_passthrough(node):
    """
    Checks if there are passthrough variables which aren't assigned.
    That happens inside ClassDef because DeFree cannot put arguments into
    Classes the way it does for functions.
    DeClass takes care of this.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
            self.stack = []
        
        def visit(self, node):
            if hasattr(node, "scopes"):
                self.stack.append(set())
                ast.NodeVisitor.visit(self, node)
                self.stack.pop()
            else:
                ast.NodeVisitor.visit(self, node)
            
        def visit_Name(self, node):
            _, components = naming.decode_id(node.id)
            if "P" in components:
                # this is a passthrough variable
                if isinstance(node.ctx, ast.Load):
                    if node.id not in self.stack[-1]:
                        self.found = True
                else:
                    self.stack[-1].add(node.id)
            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found

def check_global(node):
    """
    Check if there are global variables that aren't pydron built-ins.
    `None`, `True`, and `False` don't count as globals.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit(self, node):  
            if not isinstance(node, ast.Module) and hasattr(node, "scopes"):
                for var, scope in node.scopes.iteritems():
                    is_global = scope == scoping.Scope.GLOBAL
                    is_builtin = var.startswith("__pydron")
                    is_special = var == "None" or var == "True" or var == "False"
                    if is_global and not is_builtin and not is_special:
                        self.found = True
            ast.NodeVisitor.visit(self, node)

         
            
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


def check_deletevar(node):
    """
    Check if there is a delete statement for a variable. Deletes for
    attributes and subscripts don't count.
    """
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
        
        def visit_Delete(self, node):  
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.found = True

    visitor = Visitor()
    visitor.visit(node)
    return visitor.found

def check_overwrite(node):
    
    class Visitor(ast.NodeVisitor):
        
        def __init__(self):
            self.found = False
            self.stack =[]
        
        def visit_Module(self, node):  
            self.start_scope(node)
            self.generic_visit(node)
            self.end_scope(node)
            
        def visit_FunctionDef(self, node):
            self.assignment(node.name)
            
            self.start_scope(node)
            self.generic_visit(node)
            self.end_scope(node)
            
        def visit_ClassDef(self, node):
            self.assignment(node.name)
            
            self.start_scope(node)
            self.generic_visit(node)
            self.end_scope(node)
            
        def visit_arguments(self, node):
            if node.vararg:
                self.assignment(node.vararg)
            if node.kwarg:
                self.assignment(node.kwarg)
            self.generic_visit(node)
            
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Store) or isinstance(node.ctx, ast.Param):
                self.assignment(node.id)
                
        def start_scope(self, node):
            self.stack.append(set())

        def end_scope(self, node):
            self.stack.pop()
            
        def assignment(self, identifier):
            if identifier in self.stack[-1]:
                self.found = True
            else:
                self.stack[-1].add(identifier)
    
    visitor = Visitor()
    visitor.visit(node)
    return visitor.found


check_continue = make_nonexistent_check(ast.Continue)
check_assert = make_nonexistent_check(ast.Assert)
check_raise = make_nonexistent_check(ast.Raise)
check_print = make_nonexistent_check(ast.Print)
check_with = make_nonexistent_check(ast.With)
check_lambda = make_nonexistent_check(ast.Lambda)
check_setcomp = make_nonexistent_check(ast.SetComp)
check_listcomp = make_nonexistent_check(ast.ListComp)
check_dictcomp = make_nonexistent_check(ast.DictComp)
check_generator = make_nonexistent_check(ast.GeneratorExp)
check_class = make_nonexistent_check(ast.ClassDef)
check_import = make_nonexistent_check(ast.Import)
check_importfrom = make_nonexistent_check(ast.ImportFrom)
check_ifexp = make_nonexistent_check(ast.IfExp)
check_boolop = make_nonexistent_check(ast.BoolOp)
check_tryexcept = make_nonexistent_check(ast.TryExcept)
check_tryfinally = make_nonexistent_check(ast.TryFinally)
check_exec = make_nonexistent_check(ast.Exec)
check_closure_func = make_closure_check("func")
check_closure_class = make_closure_check("class")
check_slice = make_nonexistent_check(ast.Slice, ast.Ellipsis, ast.ExtSlice)
check_for = make_nonexistent_check(ast.For)
check_while = make_nonexistent_check(ast.While)

#: Features are not exisitent in python code and are only introduced by transformations.
features_not_present_in_code = {'unboundunchecked', 'unassigned_passthrough'}

#: Contains all the check functions.
all_features = {
        'break':check_break, 
        'continue':check_continue,
        'return':check_return,
        'assert':check_assert,
        'print':check_print,
        'raise':check_raise,
        'with':check_with,
        'funcdefaultvalues':check_funcdefaultvalues,
        'lambda':check_lambda,
        'setcomp':check_setcomp,
        'listcomp':check_listcomp,
        'dictcomp':check_dictcomp,
        'generator':check_generator,
        'nonexplicitmembers':check_nonexplicitmembers,
        'locals': check_locals,
        'class':check_class,
        'import':check_import,
        'importfrom':check_importfrom,
        'decorator':check_decorator,
        'complexexpr':check_complexexpr,
        'multitarget': check_multitarget,
        'ifexp': check_ifexp,
        'boolop': check_boolop,
        'tryexcept': check_tryexcept,
        'tryfinally':check_tryfinally,
        'exec':check_exec,
        'unassigned_passthrough':check_unassigned_passthrough,
        'closure_func':check_closure_func,
        'closure_class':check_closure_class,
        'global':check_global,
        'deletevar':check_deletevar,
        'overwrite':check_overwrite,
        'slice':check_slice,
        'for':check_for,
        'while':check_while
        }