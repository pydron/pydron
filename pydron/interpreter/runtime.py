# Copyright (C) 2015 Stefan C. Mueller

import signal
import time
import threading
import anycall
import twistit
from twisted.internet import reactor, defer
from pydron.config import config

import logging
from pydron.backend import worker
logger = logging.getLogger(__name__)

def ensure_reactor_running():
    """
    Starts the twisted reactor if it is not running already.
    
    The reactor is started in a new daemon-thread.
    
    Has to perform dirty hacks so that twisted can register
    signals even if it is not running in the main-thread.
    """
    if not reactor.running: #@UndefinedVariable
        
        # Some of the `signal` API can only be called
        # from the main-thread. So we do a dirty workaround.
        #
        # `signal.signal()` and `signal.wakeup_fd_capture()`
        # are temporarily monkey-patched while the reactor is
        # starting.
        #
        # The patched functions record the invocations in
        # `signal_registrations`. 
        #
        # Once the reactor is started, the main-thread
        # is used to playback the recorded invocations.
        
        signal_registrations = []

        # do the monkey patching
        def signal_capture(*args, **kwargs):
            signal_registrations.append((orig_signal, args, kwargs))
        def set_wakeup_fd_capture(*args, **kwargs):
            signal_registrations.append((orig_set_wakeup_fd, args, kwargs))
        orig_signal = signal.signal
        signal.signal = signal_capture
        orig_set_wakeup_fd = signal.set_wakeup_fd
        signal.set_wakeup_fd = set_wakeup_fd_capture
        
        
        # start the reactor in a daemon-thread
        reactor_thread = threading.Thread(target=reactor.run, name="reactor") #@UndefinedVariable
        reactor_thread.daemon = True
        reactor_thread.start()
        while not reactor.running: #@UndefinedVariable
            time.sleep(0.01)
            
        # Give the reactor a moment to register the signals. 
        # Apparently the 'running' flag is set before that.
        time.sleep(0.01)
        
        # Undo the monkey-paching
        signal.signal = orig_signal
        signal.set_wakeup_fd = orig_set_wakeup_fd
        
        # Playback the recorded calls
        for func, args, kwargs in signal_registrations:
            func(*args, **kwargs)
            


def ensure_rpcsystem():
    """
    Ensures that we have the RPC system up and running.
    Creates a TCP-based instance if required. Returns
    a deferred. Must be called from within the reactor.
    """
    if not anycall.RPCSystem.default:
        
        conf = config.load_config()
        anycall.RPCSystem.default = config.create_rpc_system(conf)
        rpcsystem = anycall.RPCSystem.default
        return rpcsystem.open()
        worker.make_worker("local", "master")# TODO remove network
    
    else:
        if not hasattr(anycall.RPCSystem.default, "local_worker"):
            worker.make_worker("local", "master") # TODO remove network
        defer.succeed(None)
    

global_scheduler_refcount = 0
global_scheduler = None    
global_pool = None

@twistit.yieldefer
def aquire_scheduler():
    global global_scheduler, global_scheduler_refcount, global_pool
    
    global_scheduler_refcount += 1
    
    # TODO: race condition if more than one aquire at the same time.
    
    if not global_scheduler:
        conf = config.load_config()
        yield ensure_rpcsystem()
        
        def on_conf_error(failure):
            logger.error(failure.getTraceback())
        
        global_pool = yield config.create_pool(conf, anycall.RPCSystem.default, on_conf_error)
        
        global_scheduler = yield defer.maybeDeferred(config.create_scheduler, conf, global_pool)
    
    defer.returnValue(global_scheduler)
    
@twistit.yieldefer
def release_scheduler():
    global global_scheduler, global_scheduler_refcount, global_pool
    
    global_scheduler_refcount -= 1
    
    if global_scheduler_refcount == 0:
        
        pool = global_pool
        global_scheduler = None
        rpcsystem = anycall.RPCSystem.default
        anycall.RPCSystem.default = None
        
        logger.debug("Stopping pool...")
        yield pool.stop()
        global_pool = None
        logger.debug("Pool stopped.")
        logger.debug("Closing RPC system...")
        yield rpcsystem.close()
        logger.debug("RPC system closed.")
    
def is_reactor_thread():
    """
    Attempts to find out if the calling thread is the reactor thread.
    """
    
    if not reactor.running: #@UndefinedVariable
        # There is no reactor thread yet.
        return False
    
    def f():
        dummy.append(threading.current_thread())
    dummy = []
    reactor.callFromThread(f) #@UndefinedVariable
    time.sleep(0.1) 
    
    if not dummy:
        # The f-call is probably waiting for this call to return to the event loop.
        return True
    else:
        return dummy[0] is threading.current_thread() 
    
    
    