# Copyright (C) 2015 Stefan C. Mueller



import logging
import anycall
logger = logging.getLogger(__name__)
    
class SchedulingStrategy(object):

    def __init__(self):
        pass
    
    def assign_jobs_to_workers(self, jobs):
        """
        Decide where to run jobs.

        Not all jobs have to be assigned to a worker. Non assigned
        jobs will be passed to the next call of the method again.
        
        It is allowed to run several jobs in parallel on the same worker.

        :param jobs: Jobs ready for execution.
        
        :returns: List of `(worker, job, callback)` tuples. 
            The callback is invoked once the job has finished.
        """
        pass
    
    def choose_source_worker(self, valueref, dest):
        """
        Decide from where `dest` should fetch
        the given value.
        
        :param valueref: Value `dest` needs.
        
        :param dest: Worker to which we need to transfer the value.
        
        :returns: source worker.
        """
        pass


def check_fixed_worker_for_job(job, master_worker):
    """
    If the given job can only run on a specific worker, this function
    will return that worker. Otherwise it will return `None`.
    
    Strategies should use this function to ensure a valid assignment.
    
    :param job: Job to check
    :param master_worker: The worker on which to run syncpoints.
    """
    props = job.g.get_task_properties(job.tick)
    
    masteronly = props.get("masteronly", False)
    syncpoint = props.get("syncpoint", False)

    syncpoint |= masteronly
    
    # Excecution must happen on `only_worker`.
    only_worker = None
    
    if syncpoint:
        only_worker = master_worker
        
    for port, valueref in job.inputs.iteritems():
        if not valueref.pickle_support:
            source = next(iter(valueref.get_workers()))
            if only_worker is not None and only_worker != source:
                raise ValueError("Job %r has no-send input port %r from %r but needs to run on %r." %
                                 (job, port, source, only_worker))
            only_worker = source
            
    return only_worker

class VerifySchedulingStrategy(SchedulingStrategy):
    def __init__(self, strategy):
        self.strategy = strategy
        self._master_worker = None
        
    def assign_jobs_to_workers(self, jobs):
        """
        Decide where to run jobs.

        Not all jobs have to be assigned to a worker. Non assigned
        jobs will be passed to the next call of the method again.
        
        It is allowed to run several jobs in parallel on the same worker.

        :param jobs: Jobs ready for execution.
        
        :returns: List of `(worker, job, callback)` tuples. 
            The callback is invoked once the job has finished.
        """
        if self._master_worker is None:
            self._master_worker = anycall.RPCSystem.default.local_remoteworker #@UndefinedVariable
        
        
        for worker, job, callback in self.strategy.assign_jobs_to_workers(jobs):
            
            fixed = check_fixed_worker_for_job(job, self._master_worker)
            if fixed is not None and worker is not fixed:
                raise ValueError("Invalid scheduling decision. Expected %r to run on %r, but was assigned to %r." %
                                 (job, fixed, worker))
            
            yield worker, job, callback
        
    
    def choose_source_worker(self, valueref, dest):
        """
        Decide from where `dest` should fetch
        the given value.
        
        :param valueref: Value `dest` needs.
        
        :param dest: Worker to which we need to transfer the value.
        
        :returns: source worker.
        """
        worker = self.strategy.choose_source_worker(valueref, dest)
        workers = valueref.get_workers()
        if worker not in workers:
                raise ValueError("Invalid scheduling decision. Expected %r to be fetched from one of %r, but is %r." %
                                 (valueref, workers, worker))
        return worker

class TrivialSchedulingStrategy(SchedulingStrategy):
    
    def __init__(self, pool):
        self._idle_workers = set(pool.get_workers())
        self._busy_workers = set()
        self._master_worker = None
        
    def assign_jobs_to_workers(self, jobs):
        if self._master_worker is None:
            self._master_worker = anycall.RPCSystem.default.local_remoteworker #@UndefinedVariable
        
        while jobs:
            job = jobs.pop()
            
            worker, callback = self._assign_job_to_worker(job)
            if worker is not None:
                yield worker, job, callback
            
            
    def _assign_job_to_worker(self, job):
            
        props = job.g.get_task_properties(job.tick)
        quick = props.get("quick", False)
        
        worker = check_fixed_worker_for_job(job, self._master_worker)
        
        if worker is None and quick:
            # run quick jobs on master
            worker = self._master_worker
            
        if worker is None and self._idle_workers:
            # run slow jobs on an idle worker
            worker = next(iter(self._idle_workers))
            
        if worker is None:
            return None, None
        
        if quick:
            return worker, None
        else:
            
            if worker in self._busy_workers:
                return None, None
            
            was_idle = worker in self._idle_workers
            
            if was_idle:
                self._idle_workers.remove(worker)
                
            self._busy_workers.add(worker)
            
            def callback(job, worker, worker_is_dead):
                if was_idle and not worker_is_dead:
                    self._idle_workers.add(worker)
                self._busy_workers.remove(worker)
            
            return worker, callback

    def choose_source_worker(self, valueref, dest):
        workers = list(valueref.get_workers())
        if len(workers) == 0:
            raise KeyError("%r is not stored on any workers." % valueref.valueid)
        
        if len(workers) == 1:
            # If there is a source we have to return it.
            return workers[0]
        
        return next(iter(workers))