# Copyright (C) 2015 Stefan C. Mueller

from pydron.dataflow import graph
from pydron.interpreter import runtime, traverser
from pydron.backend import worker

from twisted.internet import defer, threads, reactor

import logging
import twistit
from twisted.python import failure
import anycall
logger = logging.getLogger(__name__)


class FailureError(Exception):
    def __init__(self, func, failure):
        self.func = func
        self.failure = failure
    def __repr__(self):
        return "FailureError(%r, %s)" % (self.func, self.failure.getTraceback())
    def __str__(self):
        return repr(self)
    
def wrap_failure(function):
    def f(*args, **kwargs):
        d = defer.maybeDeferred(function, *args, **kwargs)
        def on_failure(reason):
            return failure.Failure(FailureError(function, reason))
        d.addErrback(on_failure)
        return d
    return f

class BlockingScheduler(object):
    """
    Provides the blocking API required by `tasks.ScheduledCallable`.
    
    Creates the :class:`Traverser` and hooks it up to a :class:`Scheduler`.
    """

    def execute_blocking(self, g, inputs):
        
        if runtime.is_reactor_thread():
            raise ValueError("Cannot invoke functions with @schedule decorator form within twisted's reactor thread.")
        logger.debug("Ensuring reactor is running")
        runtime.ensure_reactor_running()
        
        logger.debug("Aquiring scheduler..")
        shed = threads.blockingCallFromThread(reactor, wrap_failure(runtime.aquire_scheduler))
        logger.debug("Got scheduler.")
        
        logger.info("Executing graph: %r" % g)
        
        trav = traverser.Traverser(shed.schedule_refinement, shed.schedule_evaluation)
        
        @twistit.yieldefer
        def inside_reactor():
            
            logger.debug("Making sure RPC system is up and running.")
            yield runtime.ensure_rpcsystem()
            
            logger.debug("Getting local worker")
            me = anycall.RPCSystem.default.local_worker  #@UndefinedVariable
            meremote = anycall.RPCSystem.default.local_remoteworker #@UndefinedVariable
            
            # Injest the inputs into the local worker
            # so that we can pass valueref's to the traverser
            logger.debug("Injesting graph inputs")
            graph_inputs = {}
            for port, value in inputs.iteritems():
                valueid = worker.ValueId(graph.Endpoint(graph.START_TICK, port))
                
                me.set_value(valueid, value)
                picklesupport = yield me.get_pickle_supported(valueid)
                valueref = worker.ValueRef(valueid, picklesupport, meremote)
                graph_inputs[port] = valueref
                
            logger.debug("Starting to traverse the graph.")
            graph_outputs = yield trav.execute(g, graph_inputs)
            logger.debug("Graph traversal completed, transfering graph outputs to local worker.")
            
            # Get the outputs back to the local worker
            # and extract them.
            outputs = {}
            for port, valueref in graph_outputs.iteritems():
                source = shed._strategy.choose_source_worker(valueref, meremote)
                
                logger.debug("Transferring data for port %r from %r to %r." % (port, source, me))
                yield me.fetch_from(source, valueref.valueid)
                logger.debug("Transferring data for port %r completed." % (port))
                logger.debug("Extracting data for port %r." % (port))
                value = yield me.get_value(valueref.valueid)
                logger.debug("Extracting data for port %r completed." % (port))
                outputs[port] = value

            logger.debug("Got graph outputs")
            defer.returnValue(outputs)
        
        try:
            try:
                return threads.blockingCallFromThread(reactor, wrap_failure(inside_reactor))
            except FailureError as e:
                logger.warn("Forwarding failure to user:" + e.failure.getTraceback())
                e.failure.raiseException()
        
        finally:
            logger.debug("Releasing scheduler..")
            shed = threads.blockingCallFromThread(reactor, wrap_failure(runtime.release_scheduler))
            logger.debug("Scheduler released")
