# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_assign, mk_call, mk_name, mk_attr, mk_call_expr
from pydron.translation import transformer



class DeWith(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'with'}
    
    #: List of features added to the AST.
    added_features = {'raise', 'tryexcept', 'tryfinally', 'complexexpr', 'overwrite'}
    
    def __init__(self, id_factory):
        self.id_factory = id_factory
    
    def visit_With(self, node):
        node = self.generic_visit(node)
        
        # Build equivalent code with try catch finally.
        # PEP-0343 provides the equivalent code for us.
        
        statements = []
        
        # mgr = node.expr
        mgr_id = self.id_factory("mgr")
        s = mk_assign(mgr_id, node.context_expr)
        statements.append(s)
        
        # exit = type(msg).__exit__
        exit_id = self.id_factory("exit")
        s = mk_assign(exit_id, mk_attr(mk_call('type', [mk_name(mgr_id)]), "__exit__"))
        statements.append(s)
        
        # value = type(msg).__enter__(mgr)
        value_id = self.id_factory("value")
        s = mk_assign(value_id, mk_call_expr(mk_attr(mk_call('type', [mk_name(mgr_id)]), "__enter__"), [mk_name(mgr_id)]))
        statements.append(s)
        
        # exc = True
        exc_id = self.id_factory("exc")
        s = mk_assign(exc_id, mk_name("True"))
        statements.append(s)
        
        # try:
        tryfinally_body = []
        tryfinally_finalbody = []
        s = ast.TryFinally(body=tryfinally_body, finalbody=tryfinally_finalbody)
        statements.append(s)
        
        #     try:
        tryexcept_body = []
        tryexcept_except = []
        expt_handler = ast.ExceptHandler(type=None,name=None,body=tryexcept_except)
        s = ast.TryExcept(body=tryexcept_body, handlers=[expt_handler], orelse=[])
        tryfinally_body.append(s)
        
        #         node.optional_vars = value
        if node.optional_vars:
            s = ast.Assign(targets=[node.optional_vars], value=mk_name(value_id))
            tryexcept_body.append(s)
            
        #         body
        tryexcept_body.extend(node.body)
            
        #     except:
    
        #         exc = False
        s = mk_assign(exc_id, mk_name("False"))
        tryexcept_except.append(s)
        
        #         sys.exc_info()
        sys_exc_info = mk_call_expr(mk_attr(mk_name('sys'), "exc_info"), [])
        #         exit(mgr, *sys.exc_info())
        exit_call = mk_call(exit_id, [mk_name(mgr_id)], vararg=sys_exc_info)
        #         not exit(mgr, *sys.exc_info())
        test = ast.UnaryOp(op=ast.Not(), operand=exit_call)
        
        #        if not exit(mgr, *sys.exc_info()):
        #            raise
        s = ast.If(test=test, body=[ast.Raise(type=None, inst=None, tback=None)], orelse=[])
        tryexcept_except.append(s)
        
        # finally:
        
        #     if exc:
        #       exit(mgr, None, None, None)
        exit_call = mk_call(exit_id, [mk_name(mgr_id), mk_name("None"), mk_name("None"), mk_name("None")])
        s = ast.If(test=mk_name(exc_id), body=[ast.Expr(value=exit_call)], orelse=[])
        tryfinally_finalbody.append(s)
        
        return statements