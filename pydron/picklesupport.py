# Copyright (C) 2015 Stefan C. Mueller

import importlib
import copy_reg
import types
import pickle
import sys

def _unpickle_module(name):
    return importlib.import_module(name)

def _pickle_module(mod):
    return (_unpickle_module, (mod.__name__, )) 


def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)

def _pickle_builtin_method(obj):
    instance = getattr(obj, '__self__', None)
    
    if instance is None:
        # Probably a regular built-in function.
        # In CPython they have the same
        # type.
        return _pickle_global(obj)

    name = obj.__name__
    inst_type = type(instance)
    args = _pickle_global(inst_type)[1]
    
    try:
        descriptor = getattr(inst_type, name)
        recreated = descriptor.__get__(instance)
    except AttributeError:
        raise pickle.PicklingError(
            "Can't pickle %r: it's not found as %s.%s.__get__(inst)" %
            (obj, inst_type, name))
    
    if type(recreated.__self__) is not inst_type:
        raise pickle.PicklingError(
            "Can't pickle %r: it's not the same as %s.%s.__get__(inst)" %
            (obj, inst_type, name))
    
    args += (name, instance)
    
    return (_unpickle_builtin_method, args) 
        
def _unpickle_builtin_method(modulename, membername, methodname, instance):
    inst_type = _unpickle_global(modulename, membername)
    descriptor = getattr(inst_type, methodname)
    recreated = descriptor.__get__(instance)
    return recreated

def _pickle_global(obj):
    name = obj.__name__

    module = getattr(obj, "__module__", None)
    if module is None:
        module = pickle.whichmodule(obj, name)

    try:
        __import__(module)
        mod = sys.modules[module]
        klass = getattr(mod, name)
    except (ImportError, KeyError, AttributeError):
        raise pickle.PicklingError(
            "Can't pickle %r: it's not found as %s.%s" %
            (obj, module, name))
    else:
        if klass is not obj:
            raise pickle.PicklingError(
                "Can't pickle %r: it's not the same object as %s.%s" %
                (obj, module, name))
        
    return (_unpickle_global, (module, name)) 
        
        
def _unpickle_global(modulename, membername):
    mod = importlib.import_module(modulename)
    return getattr(mod, membername)
        
        
def register():
    """
    Add support for some more types to pickle.
    """
    copy_reg.pickle(types.ModuleType, _pickle_module)
    copy_reg.pickle(types.MethodType, _pickle_method)
    
    del pickle.Pickler.dispatch[types.BuiltinMethodType]
    copy_reg.pickle(types.BuiltinMethodType , _pickle_builtin_method)


register()