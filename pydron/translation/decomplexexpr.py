# Copyright (C) 2015 Stefan C. Mueller

import ast

from pydron.translation.astwriter import mk_assign, mk_name, mk_not, mk_call,\
    mk_list
from pydron.translation import transformer


ast.Assign._fields = ['value', 'targets']



class DeComplexExpr(transformer.AbstractTransformer):
    """
    Splits combined expressions into several statements.
    The resulting code has only one expression per statement.
    
    Implementation Notes:
    
    Primitive Expression: One of  `ast.Name`, `ast.Str`, and `ast.Num`.
    
    Single Expression: Syntax tree containing an arbitrary
      expression node at the root, but child expressions are
      limited to primitive expressions.
      
    Complex Expression: Arbitrary syntax tree with a root node
      derived from  `ast.expr`.
      
    
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = {'decorator',  
                            'multitarget', 
                            'with', 
                            'print',
                            'import',
                            'setcomp',
                            'dictcomp',
                            'tryexcept',
                            'tryfinally',
                            'assert',
                            'exec'}
    
    #: List of features that are removed from the AST.
    removed_features = {'complexexpr', 'lambda', 'ifexp' ,'generator', 'boolop', 'listcomp'}
    
    #: List of features added to the AST.
    added_features = {'funcdefaultvalues' , 'overwrite', 'for'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
        self.stack = []
        
    def start_frame(self):
        self.stack.append([])
    
    def end_frame(self):
        return self.stack.pop()
    
    def execute(self, statement):
        if isinstance(statement, list):
            self.stack[-1].extend(statement)
        else:
            self.stack[-1].append(statement)
    
    def generic_statement(self, node):
        self.start_frame()
        node = self.generic_visit(node)
        node = self.make_simple(node)
        return self.end_frame() + [node]
    
    def context_statement(self, node):
        self.start_frame()
        node = self.generic_visit(node)
        return self.end_frame() + [node]

    def make_simple(self, node):
        for field in node._fields:
            self.make_field_primitive(node, field)
        return node
    
    def make_field_primitive(self, node, field):
        value = getattr(node, field)
        if value is None:
            return
        if isinstance(value, list):
            value = [self.make_primitive(e) for e in value]
        else:
            value = self.make_primitive(value)
        setattr(node, field, value)

    def make_primitive(self, expr):
        if expr is None:
            return None
        if isinstance(expr, str):
            return expr
        expr = self.visit(expr)
        if isinstance(expr, ast.expr) and not is_primitive(expr):
            nicename = expr.__class__.__name__.lower()
            var = self.id_factory(nicename)
            self.execute(mk_assign(var, expr))
            return mk_name(var)
        else:
            return expr
        
    visit_Return = generic_statement
    visit_AugAssign = context_statement
    visit_Delete = context_statement
    visit_BinOp = make_simple
    visit_UnaryOp = make_simple
    visit_Expr = context_statement
    visit_Dict = make_simple
    visit_Set = make_simple
    visit_Yield = make_simple
    visit_Repr = make_simple
    visit_List = make_simple
    visit_Tuple = make_simple
    visit_Slice = make_simple
    visit_Index = make_simple
    visit_Index = make_simple
    
    
    def assign_special(self, target, value):
        """
        Returns one or more statements that perform the equlivalent
        of `target = value`.
        """
        if isinstance(target, ast.Name):
            raise ValueError("not special")
        elif isinstance(target, ast.Tuple):
            return self.assign_to_tuple_or_list(target, value)
        elif isinstance(target, ast.List):
            return self.assign_to_tuple_or_list(target, value)
        elif isinstance(target, ast.Attribute):
            return self.assign_attribute(target, value)
        elif isinstance(target, ast.Subscript):
            return self.assign_subscript(target, value)
        else:
            raise ValueError("not supported")
    
    def assign_to_tuple_or_list(self, target, value):
        """
        Returns one or more statements that perform the equlivalent
        of `target = value`. `target` as to be either a `ast.Tuple`
        or `ast.List` with `Store` context.
        """
        new_elts = []
        stmts = []
        for elt in target.elts:
            if isinstance(elt, ast.Name):
                new_elt = elt
            else:
                new_elt_id = self.id_factory("tuple")
                new_elt = ast.Name(id = new_elt_id, ctx=ast.Store())
                stmts.extend(self.assign_special(elt, mk_name(new_elt_id)))                
            new_elts.append(new_elt)
            
        target.elts = new_elts
        stmts.insert(0, ast.Assign(targets=[target], value=value))
        return stmts
    
    def assign_attribute(self, target, value):
        """
        Returns one or more statements that perform the equlivalent
        of `target = value`. `target` as to be a `ast.Attribute` with
        `Store` context.
        """
        self.start_frame()
        target.value = self.make_primitive(target.value)
        return self.end_frame() + [ast.Assign(targets=[target], value=value)]
    
    def assign_subscript(self, target, value):
        """
        Returns one or more statements that perform the equlivalent
        of `target = value`. `target` as to be a `ast.Subscript` with
        `Store` context.
        """
        self.start_frame()
        target.value = self.make_primitive(target.value)
        target.slice = self.visit(target.slice)
        return self.end_frame() + [ast.Assign(targets=[target], value=value)]
    
    def visit_Assign(self, node):
        self.start_frame()
        target = node.targets[0]
        if isinstance(target, ast.Name):
            node.value = self.visit(node.value)
            return self.end_frame() + [node]
        else:
            value = self.make_primitive(node.value)
            return self.end_frame() + self.assign_special(target, value)
    
    def visit_AugAssign(self, node):
        self.start_frame()
        node = self.generic_visit(node)
        node.value = self.make_primitive(node.value)
        return self.end_frame() + [node]
    
    def visit_FunctionDef(self, node):
        self.start_frame()
        self.generic_visit(node)
        return self.end_frame() + [node]
    
    def visit_BoolOp(self, node):
        target = self.id_factory("boolop")
        if isinstance(node.op, ast.And):
            def recursive(values):
                if len(values) == 1:
                    self.start_frame()
                    stmt = mk_assign(target, self.visit(values[0]))
                    return self.end_frame() + [stmt]
                else:
                    self.start_frame()
                    value = self.make_primitive(values[0])
                    body = recursive(values[1:])
                    orelse = [mk_assign(target, value)]
                    ifstmt = ast.If(test=value, body=body, orelse=orelse)
                    return self.end_frame() + [ifstmt]
            
            self.execute(recursive(node.values))
            return mk_name(target)
        
        elif isinstance(node.op, ast.Or):
            
            def recursive(values):
                if len(values) == 1:
                    self.start_frame()
                    stmt = mk_assign(target, self.visit(values[0]))
                    return self.end_frame() + [stmt]
                else:
                    self.start_frame()
                    value = self.make_primitive(values[0])
                    orelse = recursive(values[1:])
                    body = [mk_assign(target, value)]
                    ifstmt = ast.If(test=value, body=body, orelse=orelse)
                    return self.end_frame() + [ifstmt]
        
            self.execute(recursive(node.values))
            return mk_name(target)
        
        else:
            raise ValueError("invalid boolop")
            
            
    
    def visit_BoolOp_old(self, node):
        if len(node.values) > 2:
            raise ValueError("cannot handle that yet. Maybe reduce in a separate step")
        
        left = node.values[0]
        left = self.visit(left)
        left = self.make_primitive(left)
        if isinstance(node.op, ast.And):
            condition = mk_not(left)
            condition = self.make_primitive(condition)
        else:
            condition = left
        
        self.start_frame()
        right = node.values[1]
        right = self.visit(right)
        right = self.make_primitive(right)
        right_statements = self.end_frame()
        
        result = self.id_factory("boolop")
            
        # if condition:
        #   result = left
        # else:
        #   right_statements
        #   result = right
        
        ifs = ast.If()
        ifs.test = condition
        ifs.body = [mk_assign(result, left)]
        ifs.orelse = right_statements + [mk_assign(result, right)]
        self.execute(ifs)
        return mk_name(result)
    
    def visit_arguments(self, node):
        node.defaults = [self.make_primitive(n) for n in node.defaults]
        return node
        
    def visit_Lambda(self, node):

        function_name = self.id_factory("lambda")
        
        self.start_frame()
        body_expr = self.make_primitive(self.visit(node.body))
        body = self.end_frame()
        
        ret = ast.Return()
        ret.value = body_expr
        body.append(ret)
        
        func = ast.FunctionDef()
        func.name = function_name
        func.args = self.visit(node.args)
        func.body = body
        func.decorator_list = []
        
        self.execute(func)
        
        return mk_name(function_name)
    
    def build_comprehension(self, comp, body):
        for cond in reversed(comp.ifs):
            ifstmt = ast.If()
            ifstmt.test = cond
            ifstmt.body = body
            ifstmt.orelse = []
            body = [ifstmt]
            
        loop = ast.For()
        loop.target = comp.target
        loop.iter = comp.iter
        loop.body = body
        loop.orelse = []
        
        return loop

    def visit_GeneratorExp(self, node):
        
        # first build the function that yields the elements.
        # we don't to any depth traversal here to attempt to
        # simply expressions. We do this later on the
        # function.
        yieldstmt = ast.Expr()
        yieldstmt.value = ast.Yield()
        yieldstmt.value.value = node.elt
        body = [yieldstmt]
        
        for generator in reversed(node.generators):
            loop = self.build_comprehension(generator, body)
            body = [loop]
            
        func = ast.FunctionDef()
        funcname = self.id_factory("generator")
        func.name = funcname
        args = ast.arguments()
        args.args = []
        args.vararg = None
        args.kwarg = None
        args.defaults = []
        func.args = args
        func.decorator_list = []
        func.body = body
        
        # Now simplify all expressions inside the generator.
        # We can do this now as we have a proper function
        statements = self.visit(func)
        self.execute(statements)
        
        return self.visit(mk_call(funcname))

    def visit_IfExp(self, node):
        target = self.id_factory("ifexp")
        
        self.start_frame()
        body = self.visit(node.body)
        body_stmts = self.end_frame()
        body_stmts.append(mk_assign(target, body))
        
        self.start_frame()
        orelse = self.visit(node.orelse)
        orelse_stmts = self.end_frame()
        orelse_stmts.append(mk_assign(target, orelse))
        
        ifstmt = ast.If()
        ifstmt.test = self.make_primitive(self.visit(node.test))
        ifstmt.body = body_stmts
        ifstmt.orelse = orelse_stmts
        
        self.execute(ifstmt)
        return mk_name(target)

    def visit_ListComp(self, node):
        

        listvar = self.id_factory("listcomp")
        
        self.execute(mk_assign(listvar, mk_list([])))
        
        self.start_frame()
        add = ast.AugAssign()
        add.target = ast.Name(id=listvar, ctx=ast.Store())
        add.value = self.make_primitive(mk_list([self.make_primitive(node.elt)]))
        add.op = ast.Add()
        body = self.end_frame()
        body.append(add)

        
        for generator in reversed(node.generators):
            loop = self.build_comprehension(generator, body)
            body = [loop]
            
        
        outermost_loop = body[0]
        
        # Now simplify all expressions inside the generator.
        # We can do this now as we have a proper function
        outermost_loop = self.visit(outermost_loop)
        self.execute(outermost_loop)
        
        return mk_name(listvar)
    
    def visit_Compare(self, node):
        
        if len(node.ops) == 1:
            node.left = self.make_primitive(node.left)
            node.comparators = [self.make_primitive(node.comparators[0])]
            return node

        def check(left, ops, rights):
            self.start_frame()
            
            op = ops.pop(0)
            right =  self.make_primitive(rights.pop(0))
            
            if ops:
                body = check(right, ops, rights)
            else:
                body = [mk_assign(target, mk_name("True"))]
                
            
            test = self.id_factory("test")
            self.execute(mk_assign(test, ast.Compare(left=left, ops=[op], comparators=[right])))
            self.execute(ast.If(test=mk_name(test), body=body, orelse=[]))
        
            return self.end_frame()
        
        target = self.id_factory("compare")
        self.execute(mk_assign(target, mk_name("False")))
        left =  self.make_primitive(node.left)
        
        body = check(left, list(node.ops), list(node.comparators))
        
        self.execute(body)
        return mk_name(target)
        
    def visit_ClassDef(self, node):
        self.start_frame()
        node.bases = [self.make_primitive(e) for e in node.bases]
        self.generic_visit(node)
        return self.end_frame() + [node]
    
    def visit_For(self, node):
        self.start_frame()
        node.iter = self.make_primitive(node.iter)
        
        if not isinstance(node.target, ast.Name):
            self.start_frame()
            target_expr = self.visit(node.target)
            target_stmts = self.end_frame()
            target_name = self.id_factory("target")
            node.target = ast.Name(id=target_name, ctx=ast.Store())
            assign = ast.Assign(targets=[target_expr], value=mk_name(target_name))
            target_stmts.append(assign)
            node.body = target_stmts + node.body
            
        node = self.generic_visit(node)
        return self.end_frame() + [node]
    
    def visit_While(self, node):
        self.start_frame()
        node.test = self.make_primitive(node.test)
        test_stmts = self.end_frame()
        
        node.body += test_stmts
        
        node = self.generic_visit(node)
        
        return test_stmts + [node]
        
    def visit_If(self, node):
        self.start_frame()
        node.test = self.make_primitive(node.test)
        self.generic_visit(node)
        return self.end_frame() + [node]
    
    def visit_Raise(self, node):
        self.start_frame()
        node.type = self.make_primitive(node.type)
        node.inst = self.make_primitive(node.inst)
        node.tback = self.make_primitive(node.tback)
        return self.end_frame() + [node]
    
    def visit_Call(self, node):
        node.func = self.make_primitive(node.func)
        node.args = [self.make_primitive(e) for e in node.args]
        for keyword in node.keywords:
            keyword.value = self.make_primitive(keyword.value)
        node.starargs = self.make_primitive(node.starargs)
        node.kwargs = self.make_primitive(node.kwargs)
        return node
    
def is_primitive(expr):
    return isinstance(expr, ast.Str) or isinstance(expr, ast.Num) or isinstance(expr, ast.Name)