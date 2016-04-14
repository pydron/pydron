# Copyright (C) 2014 Stefan C. Mueller

import ast

from pydron.translation.astwriter import mk_assign, mk_str, mk_name, mk_call
from pydron.translation.transformer import AbstractTransformer


class DeInterrupt(AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'break', 'continue', 'return'}
    
    #: List of features added to the AST.
    added_features =  {'complexexpr', 'boolop' , 'overwrite'}
    
    
    NONE = "0_none"
    CONTINUE = "1_continue"
    BREAK = "2_break"
    RETURN = "3_return"
    
    def __init__(self, id_factory):
        self.id_factory = id_factory

        # variable that stores the return value
        self.retval_id = self.id_factory("returnvalue")
        
        # variable in which we store which statement triggered
        self.flag_id = self.id_factory("interrupted")
        

    
    def visit_Break(self, node):
        node = self.generic_visit(node)
        return mk_assign(self.flag_id, mk_str(self.BREAK)), {"break"}, {"break"}
        
        
    def visit_Continue(self, node):
        node = self.generic_visit(node)
        return mk_assign(self.flag_id, mk_str(self.CONTINUE)), {"continue"}, {"continue"}
    
    def visit_Return(self, node):
        node = self.generic_visit(node)
        if node.value:
            retval = mk_assign(self.retval_id, node.value)
        else:
            retval = mk_assign(self.retval_id, mk_name("None"))
        flag = mk_assign(self.flag_id, mk_str(self.RETURN))
        return [retval, flag], {"return"}, {"return"}
    
    def visit_Module(self, node):
        body, _, _ = self.process_body(node.body)
        node.body = body
        return node
    
    def visit_TryExcept(self, node):
        body, interrupts, _ = self.process_body(node.body)
        node.body = body
        
        for handler in node.handlers:
            handler_body, handler_interrupts, _ = self.process_body(handler.body)
            handler.body = handler_body
            interrupts |= handler_interrupts
            
        return node, interrupts, set()
    
    def visit_TryFinally(self, node):
        body, body_interrupts, _ = self.process_body(node.body)
        finalbody, finalbody_interrupts, _ = self.process_body(node.finalbody)
        
        orig_flag = self.id_factory("interrupted")
        
        # The finalbody statements are executed even if an interrupt was triggered.
        # Those statements might overwrite or reset the flag. We store
        # the original flag in a new variable so that we can 'merge' the two
        # flags afterwards.
        store = mk_assign(orig_flag, mk_name(self.flag_id))
        finalbody.insert(0, store)
        
        # pick the flag with higher priority:
        # None < continue < break < return
        maxflag = mk_call('__pydron_max__', [mk_name(self.flag_id), mk_name(orig_flag)])
        finalbody.append(mk_assign(self.flag_id, maxflag))
        
        node.body = body
        node.finalbody = finalbody
        return node, body_interrupts | finalbody_interrupts, set()
    
    def visit_FunctionDef(self, node):
        body, interrupts, guaranteed = self.process_body(node.body)
        
        if "return" in interrupts:
            if "return" not in guaranteed:
                init = mk_assign(self.retval_id, mk_name("None"))
                body.insert(0, init)
                
            ret = ast.Return(value=mk_name(self.retval_id))
            body.append(ret)
        else:
            ret = ast.Return(value=mk_name("None"))
            body.append(ret)
            
        node.body = body
        return node
    
    def visit_If(self, node):
        body, body_interrupts, body_guaranteed = self.process_body(node.body)
        orelse, orelse_interrupts, orelse_guaranteed = self.process_body(node.orelse)
        node.body = body
        node.orelse = orelse
        return node, body_interrupts | orelse_interrupts, body_guaranteed & orelse_guaranteed
    
    def visit_With(self, node):
        body, body_interrupts, body_guaranteed = self.process_body(node.body)
        node.body = body
        return node, body_interrupts, body_guaranteed
    
    def visit_While(self, node):
        def wrap_condition(node):
            comparison = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.NONE)])
            node.test = ast.BoolOp(ast.And(), [comparison, node.test])
        return self._visit_loop(node, wrap_condition)
    
    def visit_For(self, node):
        def stop_iteration(node):
            cmp_break = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.BREAK)])
            cmp_return = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.RETURN)])
            test = ast.BoolOp(op=ast.Or(), values = [cmp_break, cmp_return])
            break_stmt = ast.Break()
            ifstmt = ast.If(test=test, body=[break_stmt], orelse=[])
            node.body.append(ifstmt)
            
        return self._visit_loop(node, stop_iteration)
        
    def _visit_loop(self, node, stop_iteration):
        
        body, body_interrupts, body_guranteed = self.process_body(node.body)
        orelse, orelse_interrupts, orelse_guranteed = self.process_body(node.orelse)
        
        # All interrupts of `orelse` propagate. Of `body` both `break` and `continue` are consumed
        # and only `return` goes on.
        for_interrupts = orelse_interrupts
        if "return" in body_interrupts:
            for_interrupts.add("return")
            
        if "break" not in body_interrupts and "return" not in body_interrupts:
            for_guranteed = orelse_guranteed
        else:
            for_guranteed = set()
        
        statements = []
        

        # Clear the 'continue' at the end of the body
        if "continue" in body_interrupts:
            # if flag == "continue":
            #    flag == None
            clearflag = mk_assign(self.flag_id, mk_str(self.NONE))
            if "continue" not in body_guranteed:
                comparison = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.CONTINUE)])
                ifstmt = ast.If(test=comparison, body=[clearflag], orelse=[])
                body.append(ifstmt)
            else:
                body.append(clearflag)
                
        # init the flags for "break" for the case when there isn't a single iteration.
        # If we 'pass on' some interrupts then body_visit will take care of this.
        if "break" in body_interrupts and "return" not in for_interrupts:
            statements.append(mk_assign(self.flag_id, mk_str(self.NONE)))

        
        # Assemble modified loop.
        node.body = body
        node.orelse = []
        
        # make the loop stop on 'break' and 'return'
        if "break" in body_interrupts or "return" in body_interrupts:
            stop_iteration(node)
            
        # Add the loop to the result
        statements.append(node)

        # `orelse`
        if "break" in body_interrupts or "return" in body_interrupts:
            # the `orelse` section may or may not execute
            
            if "break" in body_interrupts:
                # if flag == "break":
                #    flag == None
                clearflag = mk_assign(self.flag_id, mk_str(self.NONE))
                comparison = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.BREAK)])
                clear_break = [ast.If(test=comparison, body=[clearflag], orelse=[])]
            else:
                clear_break = []
                
            if not orelse:
                statements.extend(clear_break)
            else:
                # if flag == None
                #     ORELSSE
                # else:
                #     clear_break
                comparison = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.NONE)])
                orelse_if = ast.If(test=comparison, body=orelse, orelse=clear_break)
                statements.append(orelse_if)
        else:
            # there is no `break` therefore `orelse` is always executed.
            statements.extend(orelse)

        return statements, for_interrupts, for_guranteed


    def wrap_with_if(self, stmt_iter, candidates):
        """
        Wraps statements in an `if` statement so that they only execute
        if no interrupts have triggered.
        
        Returns the `if` statement and a set of interrupts that might
        trigger inside the body.
        """
        ifbody, additional_interrupts, _ = self.process_body(stmt_iter)

        if ifbody:
            comparison = ast.Compare(left=mk_name(self.flag_id), ops=[ast.Eq()], comparators=[mk_str(self.NONE)])
            ifstmt = ast.If(test=comparison, body=ifbody, orelse=[])
            return [ifstmt], additional_interrupts, set()
        else:
            # there are no statements, so we don't have to put an `if` around them.
            return [], additional_interrupts, set()
        
        
    def process_body(self, stmts):
        """
        Processes a sequence of statements.
        
        The returned code contains no interrupt statements
        and acts the same way the original code would, assuming
        that the first statement is executed (we don't handle
        interrupts that happen before).
        
        Returns a list of statements and a set with all interrupts
        that might be triggered within those statements.
        """
        stmt_iter = iter(stmts)
        body = []
        for stmt in stmt_iter:
            
            stmt, candidates, guaranteed = self.visit_with_interrupts(stmt)
            
            
            # If we know for sure that an interrupt will trigger, we
            # can remove the reminder of the statements.
            if guaranteed:
                self._merge(body, stmt)
                return body, candidates, guaranteed
            
            # If the previous statement might have interrupted,
            # we wrap all the remaining statements in an `if`
            # statement.
            elif candidates:
                
                # initialize the flag varible, so that it is defined
                # even if the interrupt does not trigger.
                # This happens before the statement that might trigger.
                init = mk_assign(self.flag_id, mk_str(self.NONE))
                body.insert(-1, init)
                
                self._merge(body, stmt)
               
                ifstmts, more_candidates, _ = self.wrap_with_if(stmt_iter, candidates)
                body.extend(ifstmts)
                
                # The rest of the body might trigger other
                # interrupts as well.
                return body, candidates | more_candidates, set()
            
            else:
                self._merge(body, stmt)
            
        return body, set(), set()
        
        
    def visit_with_interrupts(self, node):
        """
        Same as `self.visit(node)` but it returns the set of
        potentially triggered interrupts as well.
        """
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        retval = visitor(node)
        
        
        try:
            stmt, interrupts, guaranteed = retval
        except TypeError:
            stmt = retval
            interrupts = set()
            guaranteed = set()
        except ValueError:
            stmt, interrupts = retval
            guaranteed = set()
        return stmt, interrupts, guaranteed
    

            
    def _merge(self, body, child):
        if isinstance(child, list):
            body.extend(child)
        else:
            body.append(child)