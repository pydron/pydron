# Copyright (C) 2015 Stefan C. Mueller

from sortedcontainers import SortedSet
from pydron.dataflow import graph

class AbstractGraphDecorator(object):
    
    def __init__(self, g):
        if len(g.get_all_ticks()) != 0:
            raise ValueError("Graph must be empty.")
        self.g = g
        
    def add_task(self, tick, task, properties={}):
        self.g.add_task(tick, task, properties)
               
    def remove_task(self, tick):
        return self.g.remove_task(tick)
            
    def connect(self, source, dest):
        return self.g.connect(source, dest)
    
    def disconnect(self, source, dest):
        return self.g.disconnect(source, dest)

    def get_all_ticks(self):
        return self.g.get_all_ticks()
    
    def get_task(self, tick):
        return self.g.get_task(tick)
    
    def get_task_properties(self, tick):
        return self.g.get_task_properties(tick)
        
    def set_task_property(self, tick, key, value):
        return self.g.set_task_property(tick, key, value)
        
    def get_in_connections(self, tick):
        return self.g.get_in_connections(tick)
                
    def get_out_connections(self, tick):
        return self.g.get_out_connections(tick)
    
    def __getattr__(self, attr):
        return getattr(self.g, attr)
    
    def __repr__(self):
        return repr(self.g)
    
class DataGraphDecorator(AbstractGraphDecorator):
    """
    This decorator adds a task property called
    `out_data` to each task. The property contains
    a dict with a output-port to value mapping.
    
    Even ports that aren't currently connected
    may have data. Once the data for a particular
    port is set, it cannot be changed.
    """
    
    def __init__(self, g):
        AbstractGraphDecorator.__init__(self, g)
        self.set_task_property(graph.START_TICK, "out_data", {})

    def set_output_data(self, tick, outputs):
        """
        Set the output values of a task.
        Once an output is set, it cannot be changed.
        
        This also marks the task as 'executed'. It should
        therefore be invoked once the task has finished
        even if the task has no output ports.
        
        :param tick: Tick of the task that has completed.
        :param outputs: Dict with out-port to value-reference map. 
        """
        props = self.g.get_task_properties(tick)

        for port, data in outputs.iteritems():
            if port in props["out_data"]:
                raise ValueError("Value of out-port %s is already set." % port)
            props["out_data"][port] = data
            
    def get_data(self, out_endpoint):
        """
        Returns the data reference for the specified output port.
        
        If the data reference was not set, an error is raised.
        If the data reference was set but was returned by :meth:`gc` in
        the mean time then an error is raised too.
        """
        props = self.get_task_properties(out_endpoint.tick)
        try:
            data = props["out_data"][out_endpoint.port]
            return data
        except KeyError:
            raise KeyError("Data is not available.")
        

            
    def add_task(self, tick, task, properties={}):
        properties["out_data"] = {}
        self.g.add_task(tick, task, properties=properties)
    
        
class AbstractReadyDecorator(AbstractGraphDecorator):
    """
    Wraps a graph and keeps track of tasks that are `ready`.
    
    A task is ready if and only if:
    
     * For each input connection to certain ports: The connected output port has data set with `set_outut_data()`.
       The input ports can be selected with the `port_filter` passed to `__init__`.
     
     * The task is not a sync-point and all sync-point tasks with a lower tick have been executed.
     
     * The task is a sync-point task and all tasks with a lower tick have been executed.
     
    A task is considered to be `executed` once `set_output_data()` has been called.
    """
    
    def __init__(self, g, prefix, port_filter, property_filter, syncpoint_run_last=True):
        """
        :param prefix: Prefix for the task properties used by the implementation
          to keep track of the state. If several decorators of this type
          are wrapped around the same graph, then different prefixes must be used.
        :param port_filter: Function to filter the relevant input ports. The function
          takes three arguments:
           * The graph (`self`)
           * The tick of the task.
           * The name of the port.
          If the function returns `False` Then the port is ignored.
        :param property_filter: Function that filters tasks which are collected.
          The function takes three
           * The graph (`self`)
           * The tick of the task.
           * The properties of the task (`graph.get_task_properties(tick)`).
          Only tasks for which this function returns `True` are returned. The function
          is reevaluated if the properties of a task change.
        :param syncpoint_run_last: If `True` then tasks with syncpoints only
          run once all tasks with a lower tick have completed.
        """
        AbstractGraphDecorator.__init__(self, g)
        self._prefix = prefix
        self._port_filter = port_filter
        self._property_filter = property_filter
        self._syncpoint_run_last = syncpoint_run_last
        
        #: ticks of all tasks that have data for all inputs.
        #: That is, if every output port connected to each input port
        #: had data set with `set_output_data`.
        self._queue = SortedSet()
        
        #: ticks of all tasks with
        #: * `properties["syncpoint"] == True`
        #: * `set_output_data` not yet called.
        self._pending_syncpoints = SortedSet()
        
        #: ticks of all tasks with
        #: * `set_output_data` not yet called.
        self._pending_ticks = SortedSet()
        
        self._collected_prop = self._prefix + "_collected"
        self._count_prop = self._prefix + "_count"
        self._ready_prop = self._prefix + "_ready"
        
        self.g.set_task_property(graph.FINAL_TICK, self._count_prop, 0)
        self.g.set_task_property(graph.FINAL_TICK, self._ready_prop, 0)
        self.g.set_task_property(graph.FINAL_TICK, self._collected_prop, False)
        self._consider(graph.FINAL_TICK)
        self._pending_ticks.add(graph.FINAL_TICK)
        
    def past_all_syncpoints(self):
        """
        Returns `True` if all sync-point tasks have been executed.
        """
        return len(self._pending_syncpoints) == 0
        
    def collect_tasks(self):
        """
        Returns the ticks of all tasks which are ready.
        """
        ticks = set()
        while True:
            tick = self.consume_ready_task()
            if tick is not None:
                ticks.add(tick)
            else:
                break
        return ticks
        
    def consume_ready_task(self):
        """
        Returns the next task which is ready or `None`.
        """
        
        def check_tick_against_sync_point(tick):
            if not self._pending_syncpoints:
                return True # no more sync points
            next_sync_point = self._pending_syncpoints[0]
            
            if tick < next_sync_point:
                # `tick` is not a sync_point and must run
                # before the next sync_point.
                return True
            elif tick == next_sync_point:
                # `tick` is the sync_point
                if self._syncpoint_run_last and self._pending_ticks[0] < next_sync_point:
                    # There are still unfinished tasks that have to run
                    # before it.
                    return False
                else:
                    # It is time to run the sync_point.
                    return True
            else: # tick > next_sync_point
                # has to wait til the sync_point completed
                return False
                
        tick = next(iter(self._queue), None)
        if tick is not None:
            
            if not check_tick_against_sync_point(tick):
                return None
            
            props = self.g.get_task_properties(tick)
            if props.get(self._collected_prop, False):
                raise ValueError("Task %s became ready twice." % tick)
            self.g.set_task_property(tick, self._collected_prop, True)
            self._queue.remove(tick)
        return tick
    
    def was_collected(self, tick):
        """
        Returns if the given tick was collected.
        """
        props = self.g.get_task_properties(tick)
        return props.get(self._collected_prop, False)
        
    
    def add_task(self, tick, task, properties={}):
        properties = dict(properties)
        properties[self._count_prop] = 0
        properties[self._ready_prop] = 0
        properties[self._collected_prop] = False
        self.g.add_task(tick, task, properties=properties)
        self._consider(tick)
        self._pending_ticks.add(tick)
        if properties.get("syncpoint", False):
            self._pending_syncpoints.add(tick)
        
        
    def remove_task(self, tick):
        self.g.remove_task(tick)
        
        if tick in self._queue:
            self._queue.remove(tick)
        if tick in self._pending_syncpoints:
            self._pending_syncpoints.remove(tick)
        if tick in self._pending_ticks:
            self._pending_ticks.remove(tick)
        

    def connect(self, source, dest):
        self.g.connect(source, dest)
        
        if not self._port_filter(self, dest.tick, dest.port):
            return
    
        source_props = self.g.get_task_properties(source.tick)
        dest_props = self.g.get_task_properties(dest.tick)
    
        self.g.set_task_property(dest.tick, self._count_prop, dest_props[self._count_prop] + 1)
        
        if source.port in source_props["out_data"]:
            self.g.set_task_property(dest.tick, self._ready_prop, dest_props[self._ready_prop] + 1)

        self._consider(dest.tick)
            
    def disconnect(self, source, dest):
        self.g.disconnect(source, dest)
            
        if not self._port_filter(self, dest.tick, dest.port):
            return
            
        source_props = self.g.get_task_properties(source.tick)
        dest_props = self.g.get_task_properties(dest.tick)
    
        self.g.set_task_property(dest.tick, self._count_prop, dest_props[self._count_prop] - 1)
        
        if source.port in source_props["out_data"]:
            self.g.set_task_property(dest.tick, self._ready_prop, dest_props[self._ready_prop] - 1)
            
        self._consider(dest.tick)
            
    def set_task_property(self, tick, key, value):
        retval = AbstractGraphDecorator.set_task_property(self, tick, key, value)
        if key == "syncpoint":
            if not value and tick in self._pending_syncpoints:
                self._pending_syncpoints.remove(tick)
            if value:
                self._pending_syncpoints.add(tick)
        self._consider(tick)
        return retval
            
    def set_output_data(self, tick, outputs):
        self.g.set_output_data(tick, outputs)
        
        if tick in self._pending_syncpoints:
            self._pending_syncpoints.remove(tick)
        if tick in self._pending_ticks:
            self._pending_ticks.remove(tick)
        
        for source, dest in self.g.get_out_connections(tick):
            if source.port in outputs:
                
                if not self._port_filter(self, dest.tick, dest.port):
                    continue

                dest_props = self.get_task_properties(dest.tick)
                self.set_task_property(dest.tick, self._ready_prop, dest_props[self._ready_prop] + 1)
                self._consider(dest.tick)
         
    def _consider(self, tick):
        props = self.get_task_properties(tick)
        
        if props.get(self._collected_prop, False):
            # Already collected
            return False
        
        if props[self._count_prop] == props[self._ready_prop]:
            if self._property_filter(self, tick, props):
                should_be_in_queue = True
            else:
                should_be_in_queue = False
        else:
            should_be_in_queue = False
          
        if should_be_in_queue:
            self._queue.add(tick)
        elif tick in self._queue:
            self._queue.remove(tick)
        
class ReadyDecorator(AbstractReadyDecorator):
    """
    Wrapper around a `DataGraphDecorator` that keeps track of the
    tasks which are ready for execution.
    """
    
    def __init__(self, g):
        
        def port_filter(g, tick, port):
            return True
        
        def property_filter(g, tick, props):
            # unrefined tasks are not ready
            task = g.get_task(tick)
            if getattr(task, "refiner_ports", []):
                return props.get("refined", False)
            else:
                return True
        
        AbstractReadyDecorator.__init__(self, g, "ready", port_filter, property_filter)
        
    def collect_ready_tasks(self):
        """
        Returns all tasks for which there is data for all input connections.
        
        Only the tasks that entered this state since the last call are returned.
        
        Changes to the graph that would make a task not ready that was already
        returned by this function are not allowed.
        """
        return self.collect_tasks()
    
    def was_ready_collected(self, tick):
        """
        Returns if the tick was returned by :meth:`collect_ready_tasks`.
        """
        return self.was_collected(tick)
    
            
class RefineDecorator(AbstractReadyDecorator):
    """
    Wrapper around a `DataGraphDecorator` that keeps track of the
    tasks which are ready for refinement.
    """
    
    def __init__(self, g):
        def port_filter(g, tick, port):
            task = g.get_task(tick)
            return port in getattr(task, "refiner_ports", [])
        
        def property_filter(g, tick, props):
            return True
        
        AbstractReadyDecorator.__init__(self, g, "ref", port_filter, property_filter, syncpoint_run_last=False)
        
    def collect_refine_tasks(self):
        """
        Returns all tasks for which there is data for all input connections.
        
        Only the tasks that entered this state since the last call are returned.
        
        Changes to the graph that would make a task not ready that was already
        returned by this function are not allowed.
        """
        ticks = set()
        for tick in self.collect_tasks():
            props = self.get_task_properties(tick)
            if props[self._count_prop] > 0:
                ticks.add(tick)
        return ticks

    def was_refine_collected(self, tick):
        """
        Returns if the tick was returned by :meth:`collect_refine_tasks`.
        """
        return self.will_be_refined(tick) and self.was_collected(tick)
    
    def will_be_refined(self, tick):
        """
        Returns if the tick will be refined at all.
        """
        props = self.get_task_properties(tick)
        return props[self._count_prop] > 0