import ast

class UniqueIdentifierFactory(object):
    """
    Factory for unique python identifiers.
    """
    def __init__(self):
        self.next_nr = {}
    
    def __call__(self, nicename):
        """
        Return a new python identifier that is guaranteed to be
        unused so far.
        """
        nicename, _ = decode_id(nicename)
        nr = self.next_nr.get(nicename, 0)
        self.next_nr[nicename] = nr + 1
        return encode_id(nicename, U=nr)

def passthrough_var(name):
    nicename, components = decode_id(name)
    components['P'] = 1
    return encode_id(nicename, **components)

def encode_id(name, **components):
    if not all(len(k) == 1 and k.isalpha() and "_" not in str(v) for k, v in components.iteritems()):
        raise ValueError("name components must have a single letter key and values may not contain '_'")
    
    if components:
        encoded = name + "$" + "_".join(k + str(v) for k, v in components.iteritems())
    else:
        encoded = name
    return encoded

def decode_id(encoded_name):
    parts = iter(encoded_name.split("$"))
    try:
        name = next(parts)
        components = dict((c[0], c[1:]) for c in parts if c)
        return name, components
    except IndexError as e:
        raise type(e)("decoding '%s': %s" % (encoded_name, e.message))
    
def valid_id(encoded_name):
    name, components = decode_id(encoded_name)
    if components:
        cmps = "_".join(k + str(v) for k, v in components.iteritems())
        return name + "__" + cmps
    else:
        return name


class MakeIdsValid(ast.NodeVisitor):
    
    def visit_Name(self, node):
        node.id = valid_id(node.id)
        
    def visit_FunctionDef(self, node):
        node.name = valid_id(node.name)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        node.name = valid_id(node.name)
        self.generic_visit(node)