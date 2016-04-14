'''
Created on Oct 15, 2014

@author: stefan
'''


import ast
import scoping
from pydron.translation.astwriter import mk_call, mk_str, mk_name, mk_assign
from pydron.translation import transformer

class DeFor(transformer.AbstractTransformer):
    """
    Replaces `for` loops with `while` loops.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'for'}
    
    #: List of features added to the AST.
    added_features =  {'while', 'overwrite'}

    def __init__(self, id_factory):
        self.id_factory = id_factory

    def visit_For(self, node):
        
        node = self.generic_visit(node)
        
        iterator_id = self.id_factory("iterator")
        iter_stmt = mk_assign(iterator_id, mk_call("__pydron_iter__", [node.iter]))
    
        test = mk_call("__pydron_hasnext__", [mk_name(iterator_id)])
        
        lhs = ast.Tuple(elts=[node.target, ast.Name(id=iterator_id, ctx=ast.Store())], ctx=ast.Store())
        next_stmt = ast.Assign(targets=[lhs], value=mk_call("__pydron_next__",  [mk_name(iterator_id)]))
        node.body.insert(0, next_stmt)
        
        while_stmt = ast.While(test=test, body=node.body, orelse=node.orelse)
        ast.copy_location(while_stmt, node)
        
        return [iter_stmt, while_stmt]
    
