# Copyright (C) 2015 Stefan C. Mueller

from pydron.dataflow import graph
from pydron.interpreter import graphdecorator

from twisted.internet import defer
from twisted.internet.defer import CancelledError
from twisted.python import failure

import logging
import enum
logger = logging.getLogger(__name__)

class TaskState(enum.Enum):
    """
    State of a task during traversal.
    
    Tasks that don't need refinement won't ever be in
    states `WAITING_FOR_REFINE_INPUTS` and `REFINING`.
    
    Not all tasks will go through all states as they
    may be deleted during a refinement or have all inputs
    ready right from the beginning. Refinement (if needed)
    is guaranteed to happen before evaluation.
    """
    
    #: Task needs refinement, but we don't have
    #: the refiner inputs yet. The task has not
    #: been evaluated yet.
    WAITING_FOR_REFINE_INPUTS = 1,
    
    #: Task is currently being refined.
    #: The task has not been evaluated yet.
    REFINING = 2,
    
    #: Task needs to be evaluated, but we don't
    #: have the the inputs yet. The task
    #: is already refined or does not need
    #: refinement.
    WAITING_FOR_INPUTS = 3,
    
    #: Task is currently being evaluated.
    #: The task is refined or does not need
    #: refinement.
    EVALUATING = 4,
    
    #: Task has been evaluated.
    #: The task is refined or does not need
    #: refinement.
    EVALUATED = 5

class EvalResult(object):
    """
    Result of a task evaulation.
    """
    def __init__(self, result, duration=None, datasizes=None, transfer_results=None):
        """
        :param result: Either a :class:`failure.Failure` or a `dict` with out-port name
         to value map, where value is typically a :class:`worker.ValueId`.
         
        :param duration: Evalation time in seconds.
        
        :param datasizes: `dict` with out-port to byte-count mapping. If a port is missing
            then that implies that it's value cannot be pickled.
        
        :param transfer_results: `dict` with port to :class:`worker.TransmissionResult` mapping for
            inputs that had to be transferred first.
        """
        self.result = result
        self.duration = duration
        self.datasizes = datasizes
        self.transfer_results = transfer_results
        
    def __repr__(self):
        return "EvalResult(%r, %r, %r, %r)" % (self.result, self.duration, self.datasizes, self.transfer_results)
    

class EvaluationError(Exception):
    """
    Error while evaluating a task.
    
    :attr:`graph` Refined graph.
    :attr:`tick` Tick of the task that failed to evaluate.
    :attr:`cause` A :class`twisted.Failure` instance with the cause of the evaulation error.
    """
    def __init__(self, graph, tick, cause):
        Exception.__init__(self, "Evaluation of tick %r failed: %s" %(tick, cause.getTraceback()))
        self.graph = graph
        self.tick = tick
        self.cause = cause
        
class RefineError(Exception):
    """
    Error while refining a task.
    
    :attr:`graph` Refined graph.
    :attr:`tick` Tick of the task that failed to refine.
    :attr:`cause` A :class`twisted.Failure` instance with the cause of the refine error.
    """
    def __init__(self, graph, tick, cause):
        Exception.__init__(self, "Refinement of %r failed: %s" %(tick, cause.getTraceback()))
        self.graph = graph
        self.tick = tick
        self.cause = cause

class Traverser(object):
    """
    Traverses the graph, performs graph refinement and invokes a callback
    to ask the scheduler to execute tasks.
        
    The actual record-keeping is all done in :mod:`graphdecorator`. This is
    mostly glue code to give a nicer API for the scheduler and 
    `ScheduledCallable` based on deferreds.
    """
    
    def __init__(self, refine_task_callback, ready_task_callback):
        """
        :param ready_task_callback: function which is invoked when a task
            becomes ready for execution.
            
            It is invoked with four arguments:
             * `graph` The graph we are traversing with all the decorators around it.
             * `tick` Tick of the task.
             * `task` Task object, equal to `graph.get_task(tick)`
             * `inputs` `dict` that maps input ports to values (or rather value references).
            
            The callable has to return a deferred that maps output ports to values (or rather value references). 
            If it failbacks the traversal aborts with that failure. 
            
            The returned deferred might get cancelled if the result isn't required.
            
        :param refine_task_callback: Function which is invoked when a task
            becomes ready for refinement. The signature is the same as for`ready_task_callback`,
            the return value is ignored.
            
            The returned deferred might get cancelled if the result isn't required.
        """

                
        self._refine_task_callback = refine_task_callback
        self._ready_task_callback = ready_task_callback
        self._result = defer.Deferred(self._cancel)
        
        #: maps tick to the deferred that we passed to `ready_task_callback`.
        #: we use this to cancel the operation if needed.
        #: Contains `None` during the invocation of the callback (before we get
        #: the deferred back).
        self._pending_ready_deferreds = {}
        
        #: maps tick to the deferred that we passed to `refine_task_callback`.
        #: we use this to cancel the operation if needed.
        #: Contains `None` during the invocation of the callback (before we get
        #: the deferred back).
        self._pending_refine_deferreds = {}
        
        #: Set if a failure occured that should stop the execution and
        #: be passed on to the user.
        self._caught_failure = None
        
        self._graph = None
        self._started = False
        self._finished = False
        
        
    def get_graph(self):
        """
        Returns the graph which is refined as traversal is progressing.
        
        Once :meth:`execute` has finished, this function can be used
        to get the fully refined graph.
        """
        return self._graph
    
    def get_task_state(self, tick):
        """
        Returns the :class:`TaskState` describing the current state of the given
        task.
        """
        ready_collected = self._graph.was_ready_collected(tick)
        refine_collected = self._graph.was_refine_collected(tick)
        will_be_refined = self._graph.will_be_refined(tick)

        if tick in self._pending_refine_deferreds:
            return TaskState.REFINING
        if tick in self._pending_ready_deferreds:
            return TaskState.EVALUATING
        
        if will_be_refined:
            if refine_collected:
                if ready_collected:
                    return TaskState.EVALUATED
                else:
                    return TaskState.WAITING_FOR_INPUTS
            else:
                return TaskState.WAITING_FOR_REFINE_INPUTS

        else:
            if ready_collected:
                return TaskState.EVALUATED
            else:
                return TaskState.WAITING_FOR_INPUTS

    def execute(self, g, inputs):
        """
        Runs the given graph with the given inputs.
        
        :param g: Graph to traverse. Won't be changed.
        
        :param inputs: `dict` with port to `ValueRef` map.
        
        :returns: deferred `dict` with port to `ValueRef` map for the outputs.
            The deferred can be cancelled.
        """
        
        if self._started:
            raise ValueError("Traverser can only be started once.")
        self._started = True
        
        self._graph = graph.Graph()
        self._graph = graphdecorator.DataGraphDecorator(self._graph)
        self._graph = graphdecorator.RefineDecorator(self._graph)
        self._graph = graphdecorator.ReadyDecorator(self._graph)
        
        # copy the graph into g
        for tick in g.get_all_ticks():
            self._graph.add_task(tick, g.get_task(tick), g.get_task_properties(tick))
        for tick in g.get_all_ticks() + [graph.FINAL_TICK]:
            for source, dest in g.get_in_connections(tick):
                self._graph.connect(source, dest)

        # ingest graph inputs
        self._graph.set_output_data(graph.START_TICK, inputs)
        
        self._iterate()
        
        return self._result

    def _iterate(self):
        
        if self._finished:
            return
        
        # Stop traversing on error
        if self._caught_failure:
            self._finished = True
            self._result.errback(self._caught_failure)
            return

        # Lets see what work is ready to do
        ready_for_execution = self._graph.collect_ready_tasks()
        ready_for_refine = self._graph.collect_refine_tasks()
        
        # If the final tick is ready for execution, we have the graph
        # outputs and can finish traversing.
        if graph.FINAL_TICK in ready_for_execution:
            self._finished = True
            graph_outputs = {dest.port : self._graph.get_data(source) for source, dest in self._graph.get_in_connections(graph.FINAL_TICK)}
            self._result.callback(graph_outputs)
            return
        
        # Pass the refine jobs to the scheduler.
        for tick in ready_for_refine:
            task = self._graph.get_task(tick)
            inputs = {dest.port : self._graph.get_data(source) for source, dest in self._graph.get_in_connections(tick) if dest.port in task.refiner_ports}
            
            # We add a property to the task so that we can later check if the refine operation
            # removed the task and replaced it with a different one.
            token = object()
            self._graph.set_task_property(tick, "refine_token", token)
            
            self._pending_refine_deferreds[tick] = None
            d = self._refine_task_callback(self._graph, tick, task, inputs)
            self._pending_refine_deferreds[tick] = d
            
            def on_success(value, tick, token):
                del self._pending_refine_deferreds[tick] 
                
                # Mark the task as refined. Using the token to see if the task is still
                # in the graph.
                try:
                    token_found = self._graph.get_task_properties(tick)["refine_token"] == token
                except KeyError:
                    token_found = False
                if token_found:
                    self._graph.set_task_property(tick, "refined", True)
                
                self._iterate()
        
            def on_fail(fail, tick):
                del self._pending_refine_deferreds[tick]
                try:
                    raise RefineError(self.get_graph(), tick, fail)
                except:
                    fail = failure.Failure()
                return self._handle_failure(fail)
            
            d.addCallbacks(on_success, on_fail, callbackArgs=(tick,token), errbackArgs=(tick,))
            
            def unhandled(failure):
                logger.error(failure.getTraceback())
                
            d.addErrback(unhandled)
        
        # Pass the evaluation jobs to the scheduler.
        for tick in ready_for_execution:
            task = self._graph.get_task(tick)
            inputs = {dest.port : self._graph.get_data(source) for source, dest in self._graph.get_in_connections(tick)}
            
            self._pending_ready_deferreds[tick] = None
            d = self._ready_task_callback(self._graph, tick, task, inputs)
            self._pending_ready_deferreds[tick] = d
        
            def on_success(evalresult, tick):
                del self._pending_ready_deferreds[tick]
                
                if evalresult.duration is not None:
                    self._graph.set_task_property(tick, "eval_time", evalresult.duration)
                
                if isinstance(evalresult.result, dict):
                    outputs = evalresult.result
                    
                    if evalresult.datasizes is not None:
                        self._graph.set_task_property(tick, "datasizes", evalresult.datasizes)
                    
                    self._graph.set_output_data(tick, outputs)
                    
                        
                elif isinstance(evalresult.result, failure.Failure):
                    logger.debug("Evaluation of %r has caused exception: " % tick + evalresult.result.getTraceback())
                    
                    try:
                        raise EvaluationError(self.get_graph(), tick, evalresult.result)
                    except:
                        fail = failure.Failure()
                    
                    return self._handle_failure(fail)
                
                else:
                    raise ValueError("Unexpected result for tick %r:%r" % (tick, evalresult.result))
                
                self._iterate()
            
            def on_fail(fail, tick):
                del self._pending_ready_deferreds[tick]
            
                try:
                    raise EvaluationError(self.get_graph(), tick, fail)
                except:
                    fail = failure.Failure()
            
                return self._handle_failure(fail)
            
            d.addCallbacks(on_success, on_fail, callbackArgs=(tick,), errbackArgs=(tick,))

            def unhandled(failure):
                logger.error(failure.getTraceback())
                
            d.addErrback(unhandled)


    def _cancel(self, d):
        """
        Cancel the traversal with a CancelledError.
        """
        if self._finished:
            return
        try:
            raise CancelledError()
        except:
            self._caught_failure = failure.Failure()
            self._iterate()

    
    def _handle_failure(self, failure):
        if self._finished:
            if failure.check(CancelledError):
                return None # we cancel pending tasks on finish.
            else:
                # Cannot really do anything with this failure 
                # since we've already called back to the user.
                return failure 
        else:
            # Lets remember the failure and iterate. This
            # will cause the traversal to finish and
            # all other pending operations to be cancelled.
            self._caught_failure = failure
            self._iterate()
            return None