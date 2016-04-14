# Copyright (C) 2015 Stefan C. Mueller

from twisted.internet import defer, task, threads
import enum
import uuid
import twistit
import anycall
import logging
import pickle
from twisted.python import failure
from pydron.dataflow import graph
from pydron.interpreter import traverser
import time
import datetime
from pydron.importhook import hook

logger = logging.getLogger(__name__)


class NoPickleError(Exception):
    def __init__(self, msg="Value must not be pickled.", cause=None):
        Exception.__init__(self, msg)
        self.msg = msg
        self.cause = cause
        
    def __repr__(self):
        if self.cause is None:
            return "NoPickleError(%r)" % self.msg
        else:
            return "NoPickleError(%r, %s)" % (self.msg, self.cause.getTraceback())
        
    def __str__(self):
        return repr(self)
        
class ValueId(object):
    """
    Unique identifier for a value passed through the data-flow graph.
    
    It is essentially a `uuid`. For debugging and logging purposes
    we also store the output endpoint that produced it and an optional
    human-readable name (usually the name of the cooresponding variable
    in the code).
    """
    
    def __init__(self, endpoint, nicename=None):
        self.uuid = uuid.uuid1()
        self.endpoint = endpoint
        self.nicename = nicename
        
    def __repr__(self):
        if self.nicename:
            return "ValueId(%s, %s, %s, %s)" % (self.uuid, 
                                                self.endpoint.tick, 
                                                self.endpoint.port, 
                                                self.nicename)
        else:
            return "ValueId(%s, %s, %s)" % (self.uuid, 
                                                self.endpoint.tick, 
                                                self.endpoint.port)
    def __eq__(self, other):
        return self.uuid == other.uuid
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self.uuid)


class ValueRef(object):
    """
    Reference to a value potentially stored on a different
    worker. This is a :class:`ValueId` together with the location
    where that value is stored.
    
    A value can be stored at several places if it was transfered.
    """
    
    def __init__(self, valueid, pickle_support, *workers):
        assert isinstance(pickle_support, bool), "pickle_support must be a boolean. Is %r." % pickle_support
        self.valueid = valueid
        self._workers = set(workers)
        self.datasize = None
        self.pickle_support = pickle_support
        
    def get_workers(self):
        return self._workers
    
    def add_worker(self, worker):
        assert not isinstance(worker, Worker)
        self._workers.add(worker)
        
    def remove_worker(self, worker):
        self._workers.remove(worker)
        
    def __repr__(self):
        return "ValueRef(%r, %r, %r, %r)" % (self.valueid, self._workers, self.datasize, self.pickle_support)


class ValueContainer(object):
    """
    Object which contains the information a worker has about a value.
    This includes the value object itself and/or a pickled version of it.
    """
    
    NO_VALUE = object()
    
    def __init__(self, value=NO_VALUE, 
                 cucumber=None, 
                 pickle_supported=True, 
                 fail_if_pickle_unsupported=False):
        """
        Either `value` or `cucumber` has to be specified.
        
        :param value: The actual value object.
        :param cucumber: The pickled value object.
        :param pickle_supported: If the value can be pickled. We normally
            automatically detect this, but it can be set to `False` to
            ensure that it won't ever be pickled.
        :param fail_if_pickle_unsupported: Action if value fails to pickle. 
            If `True`, the evaluation is aborted with a :class:`NoPickleError`.
            If `False` the operation proceeds.
        """
        if not pickle_supported and fail_if_pickle_unsupported:
            raise ValueError("Cannot combine pickle_supported and fail_if_pickle_unsupported like this.")
        assert value is not self.NO_VALUE or cucumber is not None
        if not pickle_supported:
            assert cucumber is None
        self._value = value
        self._cucumber = cucumber
        self._pickle_supported = pickle_supported
        
        # Pickle the object if possible.
        if self._cucumber is None and self._pickle_supported:
            try:
                self._cucumber = pickle.dumps(self._value, pickle.HIGHEST_PROTOCOL)
                
                # This is costly, but it sometimes happens that pickling only fails
                # when unpickling.
                pickle.loads(self._cucumber)
                
            except:
                self._cucumber = None
                self._pickle_supported = False
                if fail_if_pickle_unsupported:
                    fail = failure.Failure()
                    raise NoPickleError("Value cannot be pickled", cause=fail)
        
        if self._cucumber is not None:
            self._size = len(self._cucumber)
        else:
            self._size = None
            
    def get_value(self):
        """
        Return the value object.
        """
        if self._value is self.NO_VALUE:
            # has to happen in a background thread as it might try to
            # load modules through the import hook
            
            def inthread():
                retval = pickle.loads(self._cucumber)
                return retval
            
            d = threads.deferToThread(inthread)

            def done(v):
                self._value = v
                return v
            return d
        return defer.succeed(self._value)
    
    def get_cucumber(self):
        """
        Returns the pickled value object.
        """
        if not self._pickle_supported:
            raise NoPickleError()
        return self._cucumber
    
    def get_pickle_supported(self):
        """
        Returns `True` if this value can be
        pickled. We've tried it, so this should be reliable.
        """
        return self._pickle_supported

    def get_size(self):
        """
        Returns the size of the pickled object in bytes.
        """
        if not self._pickle_supported:
            raise NoPickleError()
        return self._size


class TransmissionResult(object):
    
    def __init__(self, bytecount, duration):
        self.bytecount = bytecount
        self.duration = duration
        
    def __repr__(self):
        return "TransmissionResult(%r, %r)" % (self.bytecount, self.duration)

class PoolObserver(object):
    
    def worker_added(self, worker):
        pass
    
    def worker_removed(self, worker):
        pass
    
    def transmission_time(self, from_worker, to_worker, bytecount, duration):
        pass
    

class Pool(object):
    
    _reset_interval = 60
    
    def __init__(self):
        self.workers = []
        self._reset_loop = task.LoopingCall(self._reset)
        self._observers = []
        
    def get_workers(self):
        return self.workers
    
    def add_worker(self, worker):
        if len(self.workers) == 0:
            self._reset_loop.start(self._reset_interval, now=False)
        self.workers.append(worker)
        return worker.reset()
    
    def remove_worker(self, worker):
        self.workers.remove(worker)
        if len(self.workers) == 0:
            self._reset_loop.stop()
    
    def stop(self):
        workers = list(self.workers)
        
        ds = []
        for worker in workers:
            self.remove_worker(worker)
            d = self._stop_worker(worker)
            ds.append(d)
            
        dall = defer.DeferredList(ds, fireOnOneErrback=True)
        return dall
    
    def _stop_worker(self, worker):
        logger.debug("Stopping worker %r." % worker)
        d = worker.stop()
        def ok(_, worker):
            logger.debug("Worker %r stopped." % worker)
        def fail(reason, worker):
            logger.error("Stopping worker %r failed:" % 
                         (worker, reason.getTraceback()))
        d.addCallbacks(ok, fail, callbackArgs=(worker,), errbackArgs=(worker,))
        return d
    
    def subscribe(self, observer):
        """
        Registers an observer.
        """
        self._observers.append(observer)
        
    def unsubscribe(self, observer):
        """
        Unregisters an observer.
        """
        self._observers.remove(observer)
        
    
    def _fire_worker_added(self, worker):
        for obs in self._observers:
            obs.worker_added(worker)
            
    def _fire_worker_removed(self, worker):
        for obs in self._observers:
            obs.worker_removed(worker)
            
    def fire_transmission_time(self, from_worker, to_worker, bytecount, duration):
        for obs in self._observers:
            obs.transmission_time(from_worker, to_worker, bytecount, duration)
            
    def _reset(self):
        for w in self.workers:
            d = w.reset()
            def onfail(f):
                logging.error(f.getTraceback())
            d.addErrback(onfail)
            
        
        
class RemoteWorker(object):
    """
    Part of the worker's API that can be accessed remotely by
    other workers.
    """
    
    def __init__(self, ownid, network, nicename=None):
        
        self.ownid = ownid
        self.network = network
        if nicename is None:
            nicename = str(self.ownid)
        self.nicename = nicename
    
    def fetch_from(self, source, valueid):
        """
        Transfer a given value from the given worker to this worker.
        Returns a deferred that calls back with a :class:`TransmissionResult`
        or `None` if no transfer was required.
        """
        raise NotImplementedError("abstract")
        
    def get_cucumber(self, valueid):
        """
        Returns the pickled value (deferred).
        """
        raise NotImplementedError("abstract")
    
    def free(self, valueid):
        """
        Delete the value on the worker. 
        Returned deferred callsback with `None` once completed.
        """
        raise NotImplementedError("abstract")
    
    def copy(self, source_valueid, dest_valueid):
        """
        Creates a copy of a value. The `to_valueid` must not yet
        exist.
        """
        raise NotImplementedError("abstract")
    
    def evaluate(self, tick, task, inputs, nosend_ports=None):
        """
        Evaluate the given task with the given inputs. The inputs is a dict
        with port -> (value-id, worker) mapping. The worker is the source where
        the value should be fetched from if it isn't already available.
        
        :param nosend_ports: Output ports that should never be pickled.
        
        Returns a deferred for a :class:`EvalResult`.
        """
        raise NotImplementedError("abstract")
    
    def __repr__(self):
        return "RemoteWorker(%s)" % repr(self.nicename)


class Worker(RemoteWorker):

    def __init__(self, ownid, network, nicename=None):
        RemoteWorker.__init__(self, ownid, network, nicename)

        #: maps valueids to values or deferred that will callback once the value is loaded
        self._values = {}

    def copy(self, source_valueid, dest_valueid):
        """
        Creates a copy of a value. The `to_valueid` must not yet
        exist.
        """
        if source_valueid not in self._values:
            raise ValueError("Source of copy does not exist")
        elif dest_valueid in self._values:
            raise ValueError("Destination of value already exists.")
        
        source_holder = self._values[source_valueid]
        dest_holder = ValueHolder(dest_valueid, None)
        self._values[dest_valueid] = dest_holder

        def got_source_container(source_container):
            
            def got_value(v):
                dest_container = ValueContainer(value=v,
                                                pickle_supported=source_container.get_pickle_supported())
                dest_holder.set(dest_container)
                
            d = source_container.get_value()
            d.addCallback(got_value)
            return d
        
        d = source_holder.get()
        d.addCallback(got_source_container)
        return d
        

    def fetch_from(self, source, valueid):
        if valueid in self._values:
            holder = self._values[valueid]
            return defer.succeed(None)
        else:
            
            def cancel():
                del self._values[valueid]
                d.cancel()
                
            def success(cucumber):
                end_transmission = time.clock()
                assert isinstance(cucumber, str), "Cucumber %r is not a string." % cucumber
                container = ValueContainer(cucumber=cucumber)
                holder.set(container)
                return TransmissionResult(container.get_size(), end_transmission - start_transmission)

            def fail(failure):
                del self._values[valueid]
                holder.fail(failure)
                return failure
                
            holder = ValueHolder(valueid, canceller=cancel)
            self._values[valueid] = holder
                
            start_transmission = time.clock()
            d = defer.maybeDeferred(source.get_cucumber, valueid)
            d.addCallbacks(success, fail)
            return d
            
    
    def get_cucumber(self, valueid):
        if valueid not in self._values:
            try:
                raise KeyError("No value with id %r in worker %r." %(valueid, self))
            except:
                return defer.fail()
        def success(container):
            return container.get_cucumber()
        d = self._values[valueid].get()
        d.addCallback(success)
        return d
    
    
    def get_value(self, valueid):
        """
        Returns the unpickled value object for the given id (deferred).
        """
        if valueid not in self._values:
            try:
                raise KeyError("No value with id %r in worker %r." %(valueid, self))
            except:
                return defer.fail()
        def success(container):
            return container.get_value()
        d = self._values[valueid].get()
        d.addCallback(success)
        return d
    
    def get_size(self, valueid):
        """
        Returns the size of the pickled value in bytes.
        """
        
    def get_pickle_supported(self, valueid):
        if valueid not in self._values:
            try:
                raise KeyError("No value with id %r in worker %r." %(valueid, self))
            except:
                return defer.fail()
            
        def success(container):
            return container.get_pickle_supported()
        
        d = self._values[valueid].get()
        d.addCallback(success)
        return d
        
    
    def set_cucumber(self, valueid, cucumber):
        """
        Store the given pickled value in this worker.
        Completes immediately.
        """
        assert isinstance(cucumber, str)
        if valueid in self._values:
            raise ValueError("valueid already in use")
        container = ValueContainer(cucumber=cucumber)
        holder = ValueHolder(valueid, None)
        holder.set(container)
        self._values[valueid] = holder
        
        
    def set_value(self, valueid, value, pickle_supported=True, fail_if_pickle_unsupported=False):
        """
        Store the given unpickled value object in this worker.
        Completes immediately.
        
        :param pickle_supported: If `False` the value will never be pickled.
        
        :param fail_if_pickle_unsupported: Action if value fails to pickle. 
            If `True`, the evaluation is aborted with a :class:`NoPickleError`.
            If `False` the operation proceeds.
        
        :returns The size of the pickled value or `None` if the information
            is not available.
        """
        if not pickle_supported and fail_if_pickle_unsupported:
            raise ValueError("Cannot combine pickle_supported and fail_if_pickle_unsupported like this.")
        if valueid in self._values:
            raise ValueError("valueid already in use")
        container = ValueContainer(value=value, 
                                   pickle_supported=pickle_supported, 
                                   fail_if_pickle_unsupported=fail_if_pickle_unsupported)
        holder = ValueHolder(valueid, None)
        holder.set(container)
        self._values[valueid] = holder
        
        if container.get_pickle_supported():
            return container.get_size()
        else:
            return None
        
    def free(self, valueid):
        if valueid in self._values:
            d = self._values[valueid].free()
            
            def success(value):
                del self._values[valueid]
                return value
            
            d.addCallback(success)
            return d
        else:
            return defer.succeed(None)
        
    def reduce(self, valueid, reducer):
        """
        Returns `reducer(input)` where `input` is the value of the given valueid.
        The value has to be stored on this worker.
        """
        if valueid not in self._values:
            try:
                raise KeyError("No value with id %r in worker %r." %(valueid, self))
            except:
                return defer.fail()
        def success(container):
            
            def got_value(v):
                return reducer(v)
            d = container.get_value()
            d.addCallback(got_value)
            return d
            
        d = self._values[valueid].get()
        d.addCallback(success)
        return d
    
    def evaluate(self, tick, task, inputs, nosend_ports=None, fail_on_unexpected_nosend=False):
        """
        Evaluate the given task with the given inputs. The inputs are a dict
        with port -> (value-id, worker) mapping.
        
        :param nosend_ports: Set of output ports which must not be pickled.
        
        :param fail_on_unexpected_nosend: Action if output ports that are not in `nosend_ports`
            fail to pickle. If `True`, the evaluation is aborted with a :class:`NoPickleError`,
            if `False` the operation proceeds as if the ports where in `nosend_ports`.
        """

        logger.debug("Transfers for job %s" % tick)

        ports = []
        transfers = []
        transfer_results = {}
        for port, (valueid, worker) in inputs.iteritems():
            
            
            d = self.fetch_from(worker, valueid)
            
            def transfer_completed(transfer_result, valueid, port):
                if transfer_result: # `None` if the value was already present
                    transfer_results[port] = transfer_result
                return self.get_value(valueid)
            

            d.addCallback(transfer_completed, valueid, port)
            ports.append(port)
            transfers.append(d)
        
        d = defer.DeferredList(transfers)
            
        def run(inputs):
            """
            Runs in separate thread.
            """
            logger.debug("Running job %s" % tick)
            
            #start = time.clock()
            start = datetime.datetime.now()
            try:
                result = task.evaluate(inputs)
            except:
                result = failure.Failure()
            finally:
                #end = time.clock()
                end = datetime.datetime.now()
                
                logger.debug("Running job %s finished" % tick)
                
            #duration = end - start
            duration = (end - start).total_seconds()
            return traverser.EvalResult(result, duration)
            
        @twistit.yieldefer
        def got_all(results):
            
            logger.debug("Transfers for job %s finished" % tick)
            
            values = []
            for success, result in results:
                if not success:
                    if result.check(pickle.PickleError):
                        raise pickle.PickleError("Failed to unpickle input of %r.%r: %s" %(tick, port, result))
                    else:
                        result.raiseException()
                else:
                    values.append(result)

            inputs = dict(zip(ports, values))
            
            evalresult = yield threads.deferToThread(run, inputs)
            
            if not isinstance(evalresult.result, dict) and not isinstance(evalresult.result, failure.Failure):
                raise ValueError("Evaluation of task %r did not produce a dict or a failure. Got %r." % (task, evalresult.result))
            
            defer.returnValue(evalresult)
        
        def task_completed(evalresult):
            if isinstance(evalresult.result, dict):
                
                # Injest values into our store and replace the eval results with ValueIds.
                outputs = evalresult.result
                outs = {}
                datasizes = {}
                for port, value in outputs.iteritems():
                    valueid = ValueId(graph.Endpoint(tick, port))
                    
                    pickle_supported = True
                    if nosend_ports and port in nosend_ports:
                        pickle_supported = False
                    
                    try:
                        size = self.set_value(valueid, 
                                              value, 
                                              pickle_supported, 
                                              pickle_supported and fail_on_unexpected_nosend)
                    except NoPickleError as e:
                        e = NoPickleError("Value of output port %r cannot be pickled." % port,
                                          cause=e.cause)
                        # TODO: memory leak. We should remove the values we've set in
                        # previous loop iterations.
                        raise e
                    
                    outs[port] = valueid
                    if size is not None:
                        datasizes[port] = size    
                        
                evalresult.result = outs
                evalresult.datasizes = datasizes
                evalresult.transfer_results = transfer_results
            return evalresult
                    
        d.addCallback(got_all)
        d.addCallback(task_completed)
        return d
    
    def create_remote(self, rpcsystem):
        """
        Returns a stub that can be pickled and implements :class:`RemoteWorker`.
        """
        stub = RemoteWorker(rpcsystem.ownid, self.network, self.nicename) # TODO remove network
        stub.fetch_from = rpcsystem.create_local_function_stub(self.fetch_from)
        stub.get_cucumber = rpcsystem.create_local_function_stub(self.get_cucumber)
        stub.free = rpcsystem.create_local_function_stub(self.free)
        stub.reduce = rpcsystem.create_local_function_stub(self.reduce)
        stub.evaluate = rpcsystem.create_local_function_stub(self.evaluate)
        stub.copy = rpcsystem.create_local_function_stub(self.copy)
        assert stub.ownid == stub.evaluate.peerid # TODO: remove
        return stub

    def __repr__(self):
        return "Worker(%s)" % repr(self.nicename)

class ValueHolder(object):
    """
    Contains a value object with proper handling of transmission and freeing.
    """

    class State(enum.Enum):
        #: Data transfer in process, no pending `get` calls.
        transfering_no_waiters = 1
        
        #: Data transfer in process, pending `get` calls.
        transfering_waiters = 2
        
        #: Data transfer in process, pending `get` calls, `free` is pending.
        transfering_waiters_free = 3
        
        #: Data transfer completed.
        stored = 4
        
        #: Data was freed.
        freed = 5
    
    def __init__(self, valueid, canceller):
        """
        Creates a new value object. Assumes that the transmission to fetch
        the data has already started and will call either callback or errback.
        
        :param valueid: Value id
        :param canceller: Callable without parameters will be invoked if this
           class decides that the transfer should be aborted.
        """
        self.valueid = valueid
        self.canceller = canceller
        self._state = self.State.transfering_no_waiters
        self._value = None
        self._get_deferreds = []
        self._free_deferreds = []

    def get(self):
        """
        Returns a deferred that callbacks with the value.
        The deferred can be cancelled, but the transmission
        will only be cancelled if all deferreds are cancelled.
        """
        
        if self._state == self.State.transfering_no_waiters:
            d = defer.Deferred(self._get_canceller)
            self._get_deferreds.append(d)
            self._state = self.State.transfering_waiters
            return d
            
        elif self._state == self.State.transfering_waiters:
            d = defer.Deferred(self._get_canceller)
            self._get_deferreds.append(d)
            return d
            
        elif self._state == self.State.transfering_waiters_free:
            d = defer.Deferred(self._get_canceller)
            self._get_deferreds.append(d)
            return d
            
        elif self._state == self.State.stored:
            return defer.succeed(self._value)
        
        elif self._state == self.State.freed:
            raise ValueError("This value instance should not be used anymore")
        
        else:
            raise ValueError("Invalid state")
        
    
    def set(self, value):
        """
        Set the value. Callbacks all deferreds returned
        by :meth:`get`.
        """
        
        if self._state == self.State.transfering_no_waiters:
            self._value = value
            self._get_deferreds = None
            self._free_deferreds = None
            self._state = self.State.stored
            
        elif self._state == self.State.transfering_waiters:
            self._value = value
            for d in self._get_deferreds:
                d.callback(value)
            self._get_deferreds = None
            self._free_deferreds = None
            self._state = self.State.stored
            
        elif self._state == self.State.transfering_waiters_free:
            self._state = self.State.freed
            for d in self._get_deferreds:
                d.callback(value)
            self._get_deferreds = None
            for d in self._free_deferreds:
                d.callback(None)
            self._free_deferreds = None
            
        elif self._state == self.State.stored:
            raise ValueError("Attempt to set already set value")
        
        elif self._state == self.State.freed:
            raise ValueError("This value instance should not be used anymore")
        
        else:
            raise ValueError("Invalid state")
        
        

    def fail(self, failure):
        """
        Errbacks all deferreds returned
        by :meth:`get`.
        """
        if self._state == self.State.transfering_no_waiters:
            self._get_deferreds = None
            self._free_deferreds = None
            self._state = self.State.freed
            
        elif self._state == self.State.transfering_waiters:
            for d in self._get_deferreds:
                d.errback(failure)
            self._get_deferreds = None
            self._free_deferreds = None
            self._state = self.State.freed
            
        elif self._state == self.State.transfering_waiters_free:
            for d in self._get_deferreds:
                d.errback(failure)
            self._get_deferreds = None
            self._state = self.State.freed
            for d in self._free_deferreds:
                d.callback(None)
            self._free_deferreds = None
            
        elif self._state == self.State.stored:
            raise ValueError("Attempt to set already set value")
        
        elif self._state == self.State.freed:
            raise ValueError("This value instance should not be used anymore")
        
        else:
            raise ValueError("Invalid state")
        
        
    def free(self):
        """
        Free the stored variable as soon as all pending :meth:`get`
        calls are callbacked.
        """
        
        if self._state == self.State.transfering_no_waiters:
            self._get_deferreds = None
            self.canceller()
            self._state = self.State.freed
            return defer.succeed(None)
            
        elif self._state == self.State.transfering_waiters:
            d = defer.Deferred()
            self._free_deferreds.append(d)
            self._state = self.State.transfering_waiters_free
            return d
            
        elif self._state == self.State.transfering_waiters_free:
            d = defer.Deferred()
            self._free_deferreds.append(d)
            return d
            
        elif self._state == self.State.stored:
            self._value = None
            self._state = self.State.freed
            return defer.succeed(None)
        
        elif self._state == self.State.freed:
            raise ValueError("This value instance should not be used anymore")
        
        else:
            raise ValueError("Invalid state")
        
    def _get_canceller(self, d):
        if self._state == self.State.transfering_no_waiters:
            raise ValueError("Invalid state. There should be no deferred that can be cancelled.")
            
        elif self._state == self.State.transfering_waiters:
            self._get_deferreds.remove(d)
            if not self._get_deferreds:
                self._state = self.State.freed
                self._get_deferreds = None
                self._free_deferreds = None
                self.canceller()
            
        elif self._state == self.State.transfering_waiters_free:
            self._get_deferreds.remove(d)
            if not self._get_deferreds:
                self._get_deferreds = None
                self._state = self.State.freed
                for d in self._free_deferreds:
                    d.callback(None)
                self._free_deferreds = None
                self.canceller()
            
        elif self._state == self.State.stored:
            return
        
        elif self._state == self.State.freed:
            return
        
        else:
            raise ValueError("Invalid state")
    
        
    def __repr__(self):
        return "ValueHolder(%r" % (self.valueid)
    
        
class WorkerStarter(object):
    
    def __init__(self, smartstarter):
        self.smartstarter = smartstarter
        import pydron
        self.smartstarter.preloaded_packages.append(pydron)
        
    @twistit.yieldefer
    def start(self):
        """
        Starts a python process using the smartstarter and returns
        a RPC stub to :class:`Worker`
        """
        
        rpc = self.smartstarter.rpcsystem
        
        process = yield self.smartstarter.start()
        
        try:
        
            make_worker_url = yield process.get_function_url(make_worker)
            make_worker_stub = rpc.create_function_stub(make_worker_url)
            
            worker = yield make_worker_stub("local") # TODO remove network
            
            worker.get_function_url = process.get_function_url_stub
            
            worker.reset = rpc.create_local_function_stub(process.reset)
            worker.stop = rpc.create_local_function_stub(process.stop)
            worker.kill = rpc.create_local_function_stub(process.kill)
            worker.stdout = process.stdout.make_stub(rpc)
            worker.stderr = process.stderr.make_stub(rpc)
            worker.exited = process.exited.make_stub(rpc)

        except:
            process.kill()
            raise 
        

            
        # worker.stdout.add_callback(stdout)
        # worker.stderr.add_callback(stderr)
        
#         receiver_stub = rpc.create_local_function_stub(hook.receiver)
#         hookinstall_url = yield process.get_function_url(hook.install_hook)
#         hookinstall_url_stub = rpc.create_function_stub(hookinstall_url)
#         yield hookinstall_url_stub(receiver_stub)
        
        defer.returnValue(worker)

def make_worker(network, nicename=None):
    rpc = anycall.RPCSystem.default
    worker = Worker(rpc.ownid, network, nicename=nicename)
    rpc.local_worker = worker
    rpc.local_remoteworker = worker.create_remote(rpc)
    return worker.create_remote(rpc)

# def stdout(txt):
#     for line in txt.splitlines():
#         if line.startswith("DEBUG:"):
#             lvl = logging.DEBUG
#         elif line.startswith("INFO:"):
#             lvl = logging.INFO
#         elif line.startswith("WARNING:"):
#             lvl = logging.WARN
#         elif line.startswith("ERROR:"):
#             lvl = logging.ERROR
#         elif line.startswith("CRITICAL:"):
#             lvl = logging.CRITICAL
#         else:
#             lvl = logging.WARN
#         logger.log(lvl, "STDOUT from %r: %s" %
#                      (worker, line))
# def stderr(txt):
#     for line in txt.splitlines():
#         logger.error("STDERR from %r: %r" %
#                  (worker, line))