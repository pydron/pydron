# Copyright (C) 2014 Stefan C. Mueller

from pydron.translation.astwriter import mk_assign, mk_call
from pydron.translation import transformer

class DeMembers(transformer.AbstractTransformer):
    """
    Make it explicit what the initial members of a class are.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'nonexplicitmembers'}
    
    #: List of features added to the AST.
    added_features =  {'locals', 'global'}
    
    def __init__(self, id_factory):
        pass
    
    def visit_ClassDef(self, node):
        self.generic_visit(node)
        stmt = mk_assign('__pydron_members__', mk_call('locals'))
        node.body.append(stmt)
        return node
    
