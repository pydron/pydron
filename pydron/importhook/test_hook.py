'''
Created on 18.10.2015

@author: stefan
'''

import unittest
import mock
import hook
from twisted.internet import defer, threads
from remoot import pythonstarter, smartstarter
import anycall
from pydron.backend import worker
import utwist
import importlib
import logging
import sys
import imp
import time


logging.basicConfig(level=logging.DEBUG)

class TestHook(unittest.TestCase):
    
    def setUp(self):
        self.receiver = mock.Mock()
        self.target = hook.Hook(self.receiver)
        
    def test_find_module(self):
        self.receiver.return_value = ("foo = 1", False)
        self.assertIs(self.target, self.target.find_module("a.b.c"))
        self.receiver.assert_called_once_with("a.b.c", "module")
        
    def test_find_package(self):
        self.receiver.return_value = ("foo = 1", True)
        self.assertIs(self.target, self.target.find_module("a.b.c"))
        self.receiver.assert_called_once_with("a.b.c", "module")
        
    def test_notfound(self):
        self.receiver.side_effect = hook.ModuleNotFound("")
        self.assertIs(None, self.target.find_module("a.b.c"))
        self.receiver.assert_called_once_with("a.b.c", "module")
        
    def test_notfound_submodule(self):
        self.receiver.side_effect = hook.ModuleNotFound("")
        self.assertIs(None, self.target.find_module("a.b.c"))
        self.assertIs(None, self.target.find_module("a.d"))
        self.receiver.assert_called_once_with("a.b.c", "module")
        
    def test_notfound_other(self):
        self.receiver.side_effect = hook.ModuleNotFound("")
        self.assertIs(None, self.target.find_module("a.b.c"))
        self.assertIs(None, self.target.find_module("b"))
        self.receiver.assert_called_with("b", "module")
        
    def test_notfound_submodule2(self):
        self.receiver.side_effect = hook.ModuleNotFound("a")
        self.assertIs(None, self.target.find_module("a.b.c"))
        self.assertIs(None, self.target.find_module("a.b.d"))
        self.receiver.assert_called_once_with("a.b.c", "module")
        
    def test_notfound_other2(self):
        self.receiver.side_effect = hook.ModuleNotFound("a")
        self.assertIs(None, self.target.find_module("a.b.c"))
        self.assertIs(None, self.target.find_module("a.d"))
        self.receiver.assert_called_with("a.d", "module")
        
class HookIntegrationTest(unittest.TestCase):
    
    @defer.inlineCallbacks
    def twisted_setup(self):
        starter = pythonstarter.LocalStarter()
        self.rpc = anycall.create_tcp_rpc_system()
        anycall.RPCSystem.default = self.rpc
        
        yield self.rpc.open()
        
        self.smart = smartstarter.SmartStarter(starter, self.rpc, anycall.create_tcp_rpc_system, [])
        self.starter = worker.WorkerStarter(self.smart)
        
        self.worker = yield self.starter.start()
        url = yield self.worker.get_function_url(try_import)
        self.try_import = self.rpc.create_function_stub(url)
        
        yield self.worker.reset()
        
        self.mockimporthook = MockImportHook({"mock_module":("pass", False)})
        self.mockimporthook.install()
        
    @utwist.with_reactor
    @defer.inlineCallbacks
    def test_non_existant(self):
        actual = yield self.try_import("does_not_exist")
        self.assertFalse(actual)

    @utwist.with_reactor
    @defer.inlineCallbacks
    def test_existant(self):
        actual = yield self.try_import("mock_module")
        self.assertTrue(actual)
    
    @defer.inlineCallbacks
    def twisted_teardown(self):
        stop = self.rpc.create_local_function_stub(self.worker.stop)
        yield stop()
        yield self.rpc.close()
        
        self.mockimporthook.uninstall()
        
@defer.inlineCallbacks
def try_import(fullname):
    
    def background():
        importlib.import_module(fullname)
    try:   
        yield threads.deferToThread(background)
        defer.returnValue(True)
    except ImportError:
        defer.returnValue(False)
        

class MockImportHook(object):
    """
    Import hook to put modules into our search path but not into
    the search path of the worker (which gets all test modules in the zip file).
    """
    
    def __init__(self, modules):
        self._modules = modules
        
    def install(self):
        sys.path_hooks.append(self)
        sys.path.append("MockHook")
        time.sleep(0.2)
        
    def uninstall(self):
        sys.path.remove("MockHook")
        sys.path_hooks.remove(self)
    
    def __call__(self, path):
        if path == "MockHook":
            return self
        else:
            raise ImportError("Expected 'MockHook'")
    
    def find_module(self, fullname, path=None):
        if fullname in self._modules:
            return self
        else:
            return None
        
    def load_module(self, fullname):
        source, ispkg = self._modules[fullname]
        
        mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
        mod.__file__ = "dummy://%s" % fullname
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
            raise ImportError("Module not found")
        _, ispkg = self._modules[fullname]
        return ispkg
    
    def get_source(self, fullname):
        if fullname not in self._modules:
            raise ImportError("Module not found")
        source, _ = self._modules[fullname]
        return source
    
    def get_code(self, fullname):
        filename = "dummy://%s" % fullname
        return compile(self.get_source(fullname), filename, 'exec')
    