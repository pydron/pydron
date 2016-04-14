'''
Created on 16.10.2015

@author: stefan
'''
import sys
import imp
import importlib
import inspect
import time
from twisted.internet import threads, reactor
import logging
from pydron import utils
logger = logging.getLogger(__name__)

class ModuleNotFound(Exception):
    """
    .. attribute found_package
    
        Full name of the package closest to the requested package
        that exists. Empty string if the top-level package does not exist
        either. For example if the request is `a.b.c.d` and package `a.b` exists
        but `c` doesn't, then `found_package == 'a.b`.
    """
    def __init__(self, found_package):
        super(ModuleNotFound, self).__init__(found_package)
        self.found_package = found_package

def install_hook(receiver):
    
    def blocking(fullname, requested_type):
        
        if utils.is_reactor_thread():
            try:
                raise ImportError("Cannot import %s: Remote import from reactor thread." % fullname)
            except:
                logger.exception("Cannot import %s: Remote import from reactor thread." % fullname)
                raise

        def in_reactor():
            d = receiver(fullname, requested_type)
            return d
    
        try:
            release_count = 0
            while imp.lock_held():
                release_count += 1
                imp.release_lock()
                
            return threads.blockingCallFromThread(reactor, in_reactor)
        finally:
            
            while release_count:
                release_count -= 1
                imp.acquire_lock()

    sys.path_hooks.append(Hook(blocking))
    sys.path.append("PydronImportHook")
    time.sleep(0.2)

def receiver(fullname, requested_type):
    if requested_type == "module":
        try:
            mod = importlib.import_module(fullname)
            source = inspect.getsource(mod)
            ispkg = hasattr(mod, "__path__")
            return source, ispkg
        except:
            
            packages = fullname.split('.')
            for i in range(len(packages) - 1, 0, -1):
                pkg = ".".join(packages[:i])
                try:
                    mod = importlib.import_module(fullname)
                    source = inspect.getsource(mod)
                except:
                    pass
                else:
                    raise ModuleNotFound(pkg)
            raise ModuleNotFound("")
    else:
        raise ValueError("Not supported")
    
class Hook(object):
    
    def __init__(self, receiver):
        """
        :param receiver: Function that takes the fullname and returns
            either the module's source or throws ModuleNotFound.
        """
        self._receiver = receiver
        
        #: Keep track of what packages we've been looking already and
        #: we know not to exist.
        self._missing_packages = set()
        
        #: fullname -> package content for packages
        #: that have been found, but not yet loaded.
        self._modules = {}
        
    def __call__(self, path):
        if path == "PydronImportHook":
            return self
        else:
            raise ImportError("Expected 'PydronImportHook'")
    
    def find_module(self, fullname, path=None):
        
        if fullname in self._modules:
            # We looked for the very same module already
            return self
        
        # Look at all the parent packages and see if we already know that one
        # of them does not exist. This cuts down lots of requests for packages
        # that we don't have.
        packages = fullname.split('.')
        for i in range(1, len(packages)):
            pkg = ".".join(packages[:i])
            if pkg in self._missing_packages:
                return None

        # Lets ask for it
        try:
            source, ispkg = self._receiver(fullname, "module")
        except ModuleNotFound as e:
            
            # all the packages nested inside 'found_package' where NOT found.
            # Lets remember that.
            assert fullname.startswith(e.found_package)
            if e.found_package:
                found_packages = e.found_package.split('.')
            else:
                found_packages = []
            for i in range(len(found_packages)+1, len(packages)+1):
                pkg = ".".join(packages[:i])
                self._missing_packages.add(pkg)
                
            return None

        # We got the source
        self._modules[fullname] = (source, ispkg)
        return self
            
    def load_module(self, fullname):
        source, ispkg = self._modules[fullname]
        
        mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
        mod.__file__ = "remote://%s" % fullname
        mod.__loader__ = self
        if ispkg:
            mod.__path__ = []
            mod.__package__ = fullname
        else:
            mod.__package__ = fullname.rpartition('.')[0]
        exec(source, mod.__dict__)
        return mod
    
    def is_package(self, fullname):
        if fullname not in self._modules:
            self.find_module(fullname)
        if fullname not in self._modules:
            raise ImportError("Module not found")
        _, ispkg = self._modules[fullname]
        return ispkg
    
    def get_source(self, fullname):
        if fullname not in self._modules:
            self.find_module(fullname)
        if fullname not in self._modules:
            raise ImportError("Module not found")
        source, _ = self._modules[fullname]
        return source
    
    def get_code(self, fullname):
        filename = "remote://%s" % fullname
        return compile(self.get_source(fullname), filename, 'exec')
    
    def get_data(self, path):
        return self._receiver(path, "data")
