# Copyright (C) 2014 Stefan C. Mueller

import ast
from pydron.translation.astwriter import mk_call, mk_tuple
from pydron.translation import transformer

class DeComp(transformer.AbstractTransformer):
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = {'setcomp', 'dictcomp'}
    
    #: List of features added to the AST.
    added_features =  {'listcomp', 'complexexpr'}
    
    def __init__(self, id_factory):
        pass
    
    def visit_SetComp(self, node):
        node = self.generic_visit(node)
        listexpr = ast.ListComp(elt=node.elt, generators=node.generators)
        return mk_call('set', [listexpr])
    
    def visit_DictComp(self, node):
        node = self.generic_visit(node)
        elt = mk_tuple([node.key, node.value])
        listexpr = ast.ListComp(elt=elt, generators=node.generators)
        return mk_call('dict', [listexpr])
    
    