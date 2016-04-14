# Copyright (C) 2015 Stefan C. Mueller

import ast

from pydron.translation import features, scoping


class AbstractTransformer(ast.NodeTransformer):
    """
    Abstract base class for AST transformations that transfrom
    AST to AST with the intent to prepare it for the translation
    to a dataflow graph. The idea is to transfrom the original
    code into a simplified form.
    
    We identify the 'complexity' of the AST by the language features
    it contains. A transformer may make assumptions on features
    removed by previous transformers and it gives gurantees on the
    features in the AST after processing. All features are
    defined in :mod:`features`.
        
    `output = input - removed + added`
    
    Where `input` is the feature set of the input AST, `removed` 
    are features removed by this transfomer and `added`
    are features added by it. The features in the output will be
    a subset of `output`.
    """
    
    #: List of features that this transformer expects to be
    #: absent in the input AST. 
    unsupported_features = set()
    
    #: List of features that are removed from the AST.
    removed_features = set()
    
    #: List of features added to the AST.
    added_features = set()
    
    def checked_visit(self, node):
        """
        Like :meth:`visit` but throws an exception if the input AST contains
        features declared in `unsupported_features` or the resulting AST contains
        features it should not according to `removed_features` and `added_features`.
        """
        featureset = set(features.all_features.keys())
        if self.unsupported_features - featureset:
            raise ValueError("Unknown features: %s" % repr(self.unsupported_features - featureset))
        if self.removed_features - featureset:
            raise ValueError("Unknown features: %s" % repr(self.removed_features - featureset))
        if self.added_features - featureset:
            raise ValueError("Unknown features: %s" % repr(self.added_features - featureset))
        
        scoping.ScopeAssigner().visit(node)
        scoping.ExtendedScopeAssigner().visit(node)
        
        input_features = {feature for feature, check in features.all_features.iteritems() if check(node)}
        contained_unsupported = input_features & self.unsupported_features
        if contained_unsupported:
            raise ValueError("Input AST contains unsupported features: %s" % repr(contained_unsupported))
        
        node = self.visit(node)
        
        scoping.ScopeAssigner().visit(node)
        scoping.ExtendedScopeAssigner().visit(node)
        
        output_features = {feature for feature, check in features.all_features.iteritems() if check(node)}
        allowed_features = (input_features - self.removed_features) | self.added_features
        
        contained_unallowed = output_features - allowed_features
        if contained_unallowed:
            raise ValueError("Output AST contains features is should not: %s" % repr(contained_unallowed))
            
        return node