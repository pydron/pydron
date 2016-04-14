'''
Created on Oct 13, 2014

@author: stefan
'''
import ast
import sys
import itertools
import astor
from pydron.translation import naming

def unindent(source):
    """
    Removes the indentation of the source code that is common to all lines.
    """
    
    def normalize(line):
        normalized = []
        for i, c in enumerate(line):
            if c == " ":
                normalized.append(" ")
            elif c == '\t':
                normalized.append(8 * " ")
            else:
                normalized.append(line[i:])
                break
        return "".join(normalized)
    
    def min_indent(lines):
        idendations = []
        for line in lines:
            if not line.strip():
                continue
            if line.strip().startswith("#"):
                continue
            idendations.append(count(line))
        if not idendations:
            return 0
        else:
            return min(idendations)
            
    def count(normalized):
        count = 0
        for c in normalized:
            if c == ' ':
                count += 1
            else:
                break
        return count
    
    def trim(normalized, indent):
        indent = min(count(normalized), indent)
        return normalized[indent:]
    
    lines = [normalize(line) for line in source.splitlines()]
    indent = min_indent(lines)    
    return "\n".join(trim(line, indent) for line in lines)


class EncodeNames(ast.NodeVisitor):
    def visit_Name(self, node):
        node.id = node.id.replace("__U", "$U")
        node.id = node.id.replace("__P", "$P")
    def visit_FunctionDef(self, node):
        node.name = node.name.replace("__U", "$U")
        node.name = node.name.replace("__P", "$P")
        self.generic_visit(node)
    def visit_ClassDef(self, node):
        node.name = node.name.replace("__U", "$U")
        node.name = node.name.replace("__P", "$P")
        self.generic_visit(node)


def compare(input_src, expected_output_src, transformer_class):
    """
    Testing utility. Takes the input source and transforms it with
    `transformer_class`. It then compares the output with the given
    reference and throws an exception if they don't match.
    
    This method also deals with name-mangling.
    """
    
    uid = naming.UniqueIdentifierFactory()
    
    actual_root = ast.parse(unindent(input_src))
    EncodeNames().visit(actual_root)
    actual_root = transformer_class(uid).checked_visit(actual_root)
    actual_root = ast.fix_missing_locations(actual_root)
    actual_src = astor.to_source(actual_root)
    try:
        compile(actual_root, "<string>", 'exec')
    except:
        sys.stderr.write(actual_src)
        sys.stderr.write("\n")
        raise
    expected_root = ast.parse(unindent(expected_output_src))
    EncodeNames().visit(expected_root)
    expected_src = astor.to_source(expected_root)
    
    cmps = itertools.izip_longest(expected_src.splitlines(), actual_src.splitlines())
    for linenr, c in enumerate(cmps, 1):
        expected_line = c[0]
        actual_line = c[1]
        if expected_line != actual_line:
            sys.stderr.write(actual_src)
            sys.stderr.write("\n")
        if expected_line != actual_line:
            raise AssertionError("Line %s differs. Expected %s but got %s." % (linenr, repr(expected_line), repr(actual_line)))

    
    
