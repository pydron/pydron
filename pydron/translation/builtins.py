
__pydron_unbound__ = object()
__pydron_unbound_nocheck__ = object()

def __pydron_unbound_check__(value):
    if value is __pydron_unbound__:
        raise UnboundLocalError("local variable referenced before assignment")
    else:
        return value
    
def __pydron_unbound_unchecked__(value):
    if value is __pydron_unbound__ or value is __pydron_unbound_nocheck__:
        return __pydron_unbound_nocheck__
    else:
        return value

def __pydron_locals__(candidates):
    return {k:v for k,v in candidates.iteritems() if v is not __pydron_unbound__ and v is not __pydron_unbound_nocheck__}

class CellObject(object):
    pass
    
def __pydron_new_cell__(var):
    return CellObject()


class __pydron_wrap_closure__(object):
    def __init__(self, func, free_vars):
        self.func = func
        self.free_vars = free_vars
        
    def __get__(self, instance, owner):
        """
        Descriptor protocol so that closures can be class
        methods.
        """
        if instance is None:
            return self
        d = self
        factory = lambda self, *args, **kw: d(self, *args, **kw)
        factory.__name__ = self.func.__name__
        return factory.__get__(instance, owner)
    
    def __call__(self, *args, **kwargs):
        args = self.free_vars + args
        return self.func(*args, **kwargs)

def __pydron_assign_global__(var, value):
    globals()[var] = value

def __pydron_read_global__(var):
    import __builtin__
    if var in globals():
        return globals()[var]
    else:
        return getattr(__builtin__, var)
        

def invoke_with_defaults(func, parameters, defaults, args, kwargs):
    num_param = len(parameters)
    num_args = len(args)
    num_args_that_fit_param = min(num_param, num_args)
    num_param_without_default = num_param - len(defaults)
    
    for i in range(0, num_param):
        parameter = parameters[i]
        
        assigned_by_arg = i < num_args_that_fit_param
        assigned_by_kwargs = parameter in kwargs
        has_default = i >=num_param_without_default
        
        #  assigned_by_arg    assigned_by_kwargs               -> error
        #  assigned_by_arg   !assigned_by_kwargs               -> ok
        # !assigned_by_arg    assigned_by_kwargs               -> ok
        # !assigned_by_arg   !assigned_by_kwargs  has_default  -> use default value
        # !assigned_by_arg   !assigned_by_kwargs !has_default  -> error
    
        if assigned_by_arg and assigned_by_kwargs:
            raise TypeError("got multiple values for keyword argument '%s'" % parameter)
        elif not assigned_by_arg and not assigned_by_kwargs:
            if not has_default:
                raise TypeError("missing value for argument '%s'" % parameter)
            else:
                kwargs[parameter] = defaults[i - num_param_without_default]
            
    return func(*args, **kwargs)
            
            
def __pydron_defaults__(func, parameters, defaults):
    def wrapper(*args, **kwargs):
        return invoke_with_defaults(func, parameters, defaults, args, kwargs)
    return wrapper
    
def __pydron_print__(stream, objects, newline):
    def is_whitespace(c):
        return (c == '\f' or 
                c == "\n" or 
                c == "\r" or
                c == "\t" or
                c == "\v")
    
    import sys
    if stream is None:
        stream = sys.stdout
    
    for obj in objects:
        if not isinstance(obj, str):
            obj = str(obj)
        if stream.softspace:
            stream.write(" ")
        stream.write(obj)

        if obj and is_whitespace(obj[-1]):
            stream.softspace = False
        else:
            stream.softspace = True
    
    if newline:
        stream.write("\n")
        stream.softspace = False
        
        
def __pydron_exec__(body, locals_, globals_):
    if locals_:
        if globals_:
            exec body in locals_, globals_
        else:
            exec body in locals_
    else:
        exec body
            
def __pydron_max__(a, b):
    return max(a, b)

class __pydron_iter__(object):
    
    END = object()
    
    def __init__(self, iterator):
        self.iterator = iter(iterator)
        self._next_obj = self._next()
        
    def hasnext(self):
        return self._next_obj is not self.END
    
    def next(self):
        if not self.hasnext():
            raise StopIteration()
        obj = self._next_obj
        self._next_obj = self._next()
        return obj
        
    def _next(self):
        try:
            return next(self.iterator)
        except StopIteration:
            return self.END
        
def __pydron_next__(it):
    return it.next(), it
def __pydron_hasnext__(it):
    return it.hasnext()
    

__all__ = [var for var in globals().keys() if var.startswith("__pydron")]


