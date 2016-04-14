# Copyright (C) 2015 Stefan C. Mueller

"""
Makes python code more 'sane'.
"""
import features
import deassert
import deimport
import declass
import decomp
import dedecorator
import dedefault
import defree
import deglobal
import deinterrupt
import delocals
import demembers
import deprint
import deunbound
import dewith
import decomplexexpr
import deexec
import demultitarget
import deslice
import defor

from pydron.translation import scoping, naming
import ast
import logging
import astor

logger = logging.getLogger(__name__)


class Saneitizer(object):
    
    steps = [
             dedecorator.DeDecorator,
             deslice.DeSlice,
             deexec.DeExec,
             demultitarget.DeMultiTarget,
             deimport.DeImport,
             deassert.DeAssert,
             decomp.DeComp,
             deinterrupt.DeInterrupt,
             demembers.DeMembers,
             delocals.DeLocals,
             deprint.DePrint,
             #dewith.DeWith, # There is no point as long as we don't handle try/except
             decomplexexpr.DeComplexExpr,
             defor.DeFor,
             dedefault.DeDefault,
             defree.DeFree,
             declass.DeClass,
             deglobal.DeGlobal,
             deunbound.DeUnbound,
             #decomplexexpr.DeComplexExpr,
             #dedefault.DeDefault      
    ]
    
    def process(self, node, id_factory=None):
        
        if not id_factory:
            id_factory = naming.UniqueIdentifierFactory()
        
        def process_step(node, step_class):
            scoping.ScopeAssigner().visit(node)
            scoping.ExtendedScopeAssigner().visit(node)

            step = step_class(id_factory)
            node = step.visit(node)
            
            return node
        
        
        for step_class in self.steps:
            logger.debug("Applying step %s" % step_class)
            node = process_step(node, step_class)
            logger.debug("After %s:\n" % step_class + astor.to_source(node))

        node = ast.fix_missing_locations(node)
            
        return node
            
    @staticmethod
    def feature_table(): 
        all_features = sorted(features.all_features.keys())
        feature_name_length = max(len(f) for f in all_features)
        
        steps_name_length = max(len(s.__name__) for s in Saneitizer.steps)
        
        lines = []
        for i in range(feature_name_length):
            names = " ".join((list(reversed(f))[i] if i < len(f) else " ") for f in all_features)
            line = " " * steps_name_length + " " + names
            lines.insert(0, line)
        lines.append("")
        
        
        
        def character(feature, step):
            present = feature in features_present
            unsupported = feature in step.unsupported_features
            removed = feature in step.removed_features
            added = feature in step.added_features
            if present and unsupported:
                return "X"
            elif added:
                return "+"
            elif removed and not added:
                return "-"
            elif present:
                return "|"
            else:
                return " "
        
        features_present = set(all_features) - features.features_not_present_in_code
        
        initial_line = " ".join("|" if f in features_present else " " for f in all_features)
        lines.append(" " * steps_name_length + " " + initial_line)
        
        for step in Saneitizer.steps:
            flags = " ".join(character(f, step) for f in all_features)
            
            name_padded = step.__name__ + " " * (steps_name_length - len(step.__name__))
            
            line = name_padded + " " + flags
            lines.append(line)
            
            features_present = (features_present - step.removed_features) | step.added_features
            
        final_line = " ".join("|" if f in features_present else " " for f in all_features)
        lines.append(" " * steps_name_length + " " + final_line)
        
        return "\n".join(lines)