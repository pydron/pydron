# Copyright (C) 2015 Stefan C. Mueller

import threading
from frozendict import frozendict

class Tick(object):
    """
    Tick objects represent a 'time' during sequential execution of the
    corresponding python code.
    
    Tick instances can be compared and are immutable.
    """
    
    def __init__(self, elements, loopmask):
        """
        Do not use. Instead derive from other tick, such as `START_TICK`.
        """
        if len(elements) < 2:
            raise ValueError()
        if elements[0] > 1:
            raise ValueError("cannot have tick after FINAL_TICK")
        if elements[0] == 1 and elements != (1,0):
            raise ValueError("cannot have tick after FINAL_TICK")
        if not isinstance(elements, tuple) or not isinstance(loopmask, tuple):
            raise TypeError()
        if len(loopmask) != len(elements):
            raise ValueError("Loopmask does not match elements")
        for e in elements:
            if not isinstance(e, (int, long)):
                raise TypeError()
            if e < 0:
                raise ValueError("elements must be non-negative.")
        self._elements = elements
        self._loopmask = loopmask
    
    def mark_loop_iteration(self):
        """
        Marks this tick as the base tick of a loop iteration.
        """
        return Tick(self._elements, self._loopmask[:-1] + (True,))
    
    @property
    def nonloop_elements(self):
        """
        Returns a tuple of integers representing those elements of the tick that are not loop iterations.
        If two ticks share the same `nonloop_elements` then they represent the same tick (task) but 
        potentially from two different loop iterations.
        """
        return tuple(self._elements[i] for i in range(len(self._elements)) if not self._loopmask[i])
    
    @property
    def loop_elements(self):
        """
        Returns a tuple of integers representing those elements of the tick that are loop iterations.
        The first element is the outer most loop. The last element the inner most loop.
        """
        return tuple(self._elements[i] for i in range(len(self._elements)) if self._loopmask[i])
        
    def __add__(self, count):
        """
        Returns the clock `count` cycles after this one. 
        Does not change the loop mask.
        """
        return Tick(self._elements[:-1] + (self._elements[-1] + count,), self._loopmask)
    
    def __lshift__(self, other):
        """
        Returns a clock that is after `other` and before `other + 1` while
        retaining the order of all clocks that have been left-shifted by
        `other`.
        """
        if other == FINAL_TICK:
            raise ValueError("Cannot move beyond FINAL_TICK")
        return Tick(other._elements + self._elements[1:], other._loopmask + self._loopmask[1:])
    
    def __rshift__(self, positions):
        """
        
        """
        if not isinstance(positions, int):
            raise ValueError("Right shifting a tick expects an integer.")
        return Tick(self._elements[:-positions], self._loopmask[:-positions])
    
    def __cmp__(self, other):
        return cmp(self._elements, other._elements)
    
    def __hash__(self):
        return hash(self._elements)
    
    def __repr__(self):
        if self == START_TICK:
            return "START_TICK"
        elif self == FINAL_TICK:
            return "FINAL_TICK"
        else:
            length = len(self._elements) 
            if length == 2:
                return self._repr_element(1)
            else:
                return "(" + ", ".join(map(self._repr_element, range(1, length))) + ")"

    def _repr_element(self, index):
        if self._loopmask[index]:
            return "*%s" % self._elements[index]
        else:
            return str(self._elements[index])
        
    @staticmethod   
    def _parse_element(elt):
        elt = elt.strip()
        loop = elt.startswith("*")
        if loop:
            elt = elt[1:]
        return int(elt), loop
            
    @staticmethod   
    def parse_tick(tick):
        if isinstance(tick, Tick):
            return tick
        elif isinstance(tick, str):
            if tick == "START_TICK":
                return START_TICK
            elif tick == "FINAL_TICK":
                return FINAL_TICK
            else:
                elements = [0]
                loopmask = [False]
                elts = tick.split(",")
                for elt in elts:
                    element, loop  = Tick._parse_element(elt)
                    elements.append(element)
                    loopmask.append(loop)
                
                return Tick(tuple(elements), tuple(loopmask))
            
        elif isinstance(tick, tuple):
            return Tick((0,) + tick, (False,) * (len(tick) + 1))
        else:
            return Tick((0, tick), (False, False))

START_TICK = Tick((0,0), (False, False))
FINAL_TICK = Tick((1,0), (False, False))

class GraphObserver(object):
    """
    Base class for graph observers.
    Ignores all events by default.
    """
    
    def connected(self, source, dest):
        pass
    
    def disconnected(self, source, dest):
        pass
    
    def task_added(self, tick, task, properties):
        pass
    
    def task_removed(self, tick, task):
        pass
    
    def task_property_changed(self, tick, key, value):
        pass

class Endpoint(object):
    """
    Port of a specific node.
    """
    def __init__(self, tick, port):
        assert isinstance(tick, Tick)
        assert isinstance(port, str)
        assert port is not None
        self.tick = tick
        self.port = port

    def __repr__(self):
        return "Endpoint(%s, %s)" % (repr(self.tick), repr(self.port))

    def __eq__(self, other):
        return self.tick == other.tick and self.port == other.port

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __hash__(self):
        return hash(self.tick) + 7*hash(self.port)


class _TaskNode(object):
    """
    Used internally by :class:`Graph`.
    """
    
    def __init__(self, task, properties):
        self.task = task
        self.properties = frozendict(properties)
        self.in_connections = {}
        self.out_connections = set()
        
    def set_property(self, key, value):
        self.properties = self.properties.copy(**{key:value})
        
    def __eq__(self, other):
        if self.task != other.task:
            return False
        
        myproperties = {k:v for k,v in self.properties.iteritems() if not k.startswith("_")}
        otherproperties = {k:v for k,v in other.properties.iteritems() if not k.startswith("_")}
        
        if myproperties != otherproperties:
            return False
        
        if self.in_connections != other.in_connections:
            return False
        
        if self.out_connections != other.out_connections:
            return False
        
        return True
    
    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        raise NotImplementedError()   
        
class _Connection(object):
    """
    Used internally by :class:`Graph`.
    """
    
    def __init__(self, source, dest):
        assert isinstance(source, Endpoint)
        assert isinstance(dest, Endpoint)
        self.source = source
        self.dest = dest

    def __eq__(self, other):
        return (self.source == other.source and
                self.dest == other.dest)
        
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __hash__(self):
        return (1 *hash(self.source) + 
                3 * hash(self.dest))
        
    def __repr__(self):
        return "(%s, %s)" % (repr(self.source), repr(self.dest))


class Graph(object):
    """
    A graph consists of tasks and data-flow connections between them.
    Each task is identified by a :class:`Tick` which represents the time
    at which that task would execute in a sequential program.
    
    Each task has input and output ports. Each port has an identifier
    object which must be unique for the task. This class makes no
    assumtion on the identifier object other than comparability.
    
    An output port may be connected to zero or more input ports.
    Each input port is connected to one output port, but may be disconnected.
    
    Causality of connections must be kept: the output tick must be older 
    than the input tick. This also forbids cicles.
    
    `START_TICK` and `FINAL_TICK` are already in the graph and serve as dummy-tasks.
    One can make connections to them to mark data passed into the graph and
    out of it.
    
    The graph is observable. Observers are objects with the following methods:
    
    .. py:function:: added_task(graph, tick, task, properties)
    
    .. py:function:: removed_task(graph, tick)
    
    .. py:function:: connected(graph, source, dest)
    
    .. py:function:: disconnected(graph, source, dest)
    
    The methods are called *after* the graph has been changed. During those calls
    the graph may *not* be changed with the exception of task properties. Exceptions
    thrown in those methods leave the graph in an undefined state. Changes to
    task properties are not reported.
    """
    


    def __init__(self):
        self._ticks = {START_TICK:_TaskNode(None, {}),
                       FINAL_TICK:_TaskNode(None, {})}
        self._observers = []

    def add_task(self, tick, task, properties={}):
        """
        Adds a task at the specified tick.
        
        The new task will be unconnected.
        
        :param tick: Time at which this task executes.
        :param properties: Properties of the task.
        """
        if tick == START_TICK:
            raise ValueError("START_TICK is reserved for inputs of the graph.")
        if tick == FINAL_TICK:
            raise ValueError("FINAL_TICK is reserved for outputs of the graph.")
        
        tasknode = _TaskNode(task, properties)
        if tick in self._ticks:
            raise ValueError("Tick already has a task")
        self._ticks[tick] = tasknode
        
        self._fire_task_added(tick, task, properties)

    def remove_task(self, tick):
        """
        Removes the task at the given tick from the graph.
        The task must be unconnected.
        """
        if not tick in self._ticks:
            raise ValueError("No task which that tick")
        if self.get_in_connections(tick) or self.get_out_connections(tick):
            raise ValueError("Task is connected")
        del self._ticks[tick]
        
        self._fire_task_removed(tick)
            
    def connect(self, source, dest):
        """
        Create a connection between two tasks.
        
        :param source: Source endpoint
        :param dest: Dest endpoint
        :param throw_exists: Throw exception if connection already exists.
        
        :returns: `True` if the connection was created, False if the
        connection already exists and `throw_exists` is `False`.
        """
        
        if dest.tick < source.tick:
            raise ValueError("Destination executes before source")
        
        if source.tick == FINAL_TICK:
            raise ValueError("FINAL_TICK can only have input ports")
        
        if dest.tick == START_TICK:
            raise ValueError("START_TICK can only have output ports")
        
        
        conn = _Connection(source, dest)
        
        source_task = self._ticks[source.tick]
        dest_task = self._ticks[dest.tick]
        
        if dest.port in dest_task.in_connections:
            if dest_task.in_connections[dest.port] == conn:
                # connection already exists
                raise ValueError("The connection %s already exists" % repr(conn))
            else:
                raise ValueError("The destination port is already connected: %s " % repr(conn))
        
        if conn in source_task.out_connections:
            raise ValueError("This connection already exists")
        
        dest_task.in_connections[dest.port] = conn
        source_task.out_connections.add(conn)

        self._fire_connected(source, dest)
        return True
    
    def disconnect(self, source, dest):
        """
        Remove a connection between two tasks.
        
        :param source: Source endpoint
        :param dest: Dest endpoint
        """
        source_task = self._ticks[source.tick]
        dest_task = self._ticks[dest.tick]
        
        conn = _Connection(source, dest)
        
        if conn not in source_task.out_connections:
            raise ValueError("This connection does not exists")
        
        del dest_task.in_connections[dest.port]
        source_task.out_connections.remove(conn)
        
        self._fire_disconnected(source, dest)
    
    def get_all_ticks(self):
        """
        Returns the ticks of all tasks.
        """
        def gen():
            for tick in self._ticks.iterkeys():
                if tick != START_TICK and tick != FINAL_TICK:
                    yield tick
        return list(gen())
    
    def get_task(self, tick):
        """
        Returns the task at the given tick.
        """
        return self._ticks[tick].task
    
    def get_task_properties(self, tick):
        """
        Returns the properties for the task executed at `tick`.
        """
        return self._ticks[tick].properties
        
    def set_task_property(self, tick, key, value):
        """
        Change a property of the task at the given tick.
        """
        task = self._ticks[tick]
        task.set_property(key, value)
        
        self._fire_task_property_changed(tick, key, value)
        
    def get_in_connections(self, tick):
        """
        Returns `(source, dest)` tuples for each input
        connection of the task at the given tick.
        """
        def gen():
            task = self._ticks[tick]
            for _, conn in task.in_connections.iteritems():
                yield (conn.source, conn.dest)
        return list(gen())
                
    def get_out_connections(self, tick):
        """
        Returns `(source_endpoint, dest_endpoint)` tuples for each output
        connection of the task at the given tick.
        """
        def gen():
            task = self._ticks[tick]
            for conn in task.out_connections:
                yield (conn.source, conn.dest)
        return list(gen())
    
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
    
    def _fire_task_added(self, tick, task, properties):
        for obs in self._observers:
            obs.task_added(tick, task, properties)
            
    def _fire_task_removed(self, tick):
        for obs in self._observers:
            obs.task_removed(tick)
            
    def _fire_connected(self, source, dest):
        for obs in self._observers:
            obs.connected(source, dest)
            
    def _fire_disconnected(self, source, dest):
        for obs in self._observers:
            obs.disconnected(source, dest)
            
    def _fire_task_property_changed(self, tick, key, value):
        for obs in self._observers:
            obs.task_property_changed(tick, key, value)  
              
    def __repr__(self):
        stack = getattr(Graph, "_repr_stack", [])
        Graph._repr_stack = stack
        if any(s is self for s in stack):
            return "<recursive graph>"
        stack.append(self)
        
        def indent(s):
            lines = s.splitlines()
            return "\n   ".join(lines)
            
        def gen_arguments():
            for tick in sorted(self._ticks.iterkeys()):
                if tick == START_TICK:
                    continue
                tasknode = self._ticks[tick]
                for conn in tasknode.in_connections.itervalues():
                    yield "%s.%s -> %s.%s" % (conn.source.tick, conn.source.port, conn.dest.tick, conn.dest.port)
                
                if tick == FINAL_TICK:
                    continue
                if tasknode.properties:
                    yield repr(tick) + ": " + indent(repr(tasknode.task)) + " " + indent(repr(dict(tasknode.properties))) 
                else:
                    yield repr(tick) + ": " + indent(repr(tasknode.task))
        
        if len(self.get_all_ticks()) == 0 and len(self.get_in_connections(FINAL_TICK)) == 0:
            s = "{}"
        else:
            s = "{\n   " + "\n   ".join(gen_arguments()) + "\n}"
        stack.pop()
        return s

    def __eq__(self, other):
        with _comparison_context(self, other) as already_comparing:
            if already_comparing:
                return True
            
            for tick in sorted(self._ticks):
                
                mytask = self._ticks[tick]
                if tick not in other._ticks:
                    return False
                othertask = other._ticks[tick]
                
                if mytask != othertask:
                    return False
                
            return True
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __hash__(self):
        raise NotImplementedError("Not supported")




class _comparison_context(object):
    """
    Graphs may be recursive. We use a bit of thread-local magic
    to break the loop.
    """
    th = threading.local()
    
    def __init__(self, graph_a, graph_b):
        self.graph_a = graph_a
        self.graph_b = graph_b
        
    def getid(self):
        return (id(self.graph_a), id(self.graph_b))

    def __enter__(self):
        if not hasattr(self.th, "stack"):
            self.th.stack = []
            
        already_comparing = self.getid() in self.th.stack
        self.th.stack.append(self.getid())
        return already_comparing

    def __exit__(self, *exec_info):
        self.th.stack.pop()
    
    @classmethod
    def comparing(cls, graph_a, graph_b):
        return cls.th.already_compared.get((id(graph_a), id(graph_b)), None)


    




class graph_factory(object):
    factory_thread_local = threading.local()
    
    def __enter__(self):
        self.factory_thread_local.named_graphs = {}
    def __exit__(self, *exec_info):
        del self.factory_thread_local.named_graphs
        return False


def G(*commands):

    if commands and isinstance(commands[0], str):
        name = commands[0]
        commands = commands[1:]
    else:
        name = None
        
    if name:
        g = graph_factory.factory_thread_local.named_graphs.get(name, Graph())
        graph_factory.factory_thread_local.named_graphs[name] = g
    else:
        g = Graph()
    
    tasks = [cmd for cmd in commands if isinstance(cmd, T)]
    connections = [cmd for cmd in commands if isinstance(cmd, C)]
    
    for task in tasks:
        g.add_task(task.tick, task.task, task.properties)
        
    for conn in connections:
        g.connect(conn.source, conn.dest)
    
    return g
            
class T (object):
    def __init__(self, tick, task, properties={}):
        self.tick = Tick.parse_tick(tick)
        self.task = task
        self.properties = properties
        
class C(object):
    def __init__(self, source_tick, source_port, dest_tick, dest_port):        
        self.source = Endpoint(Tick.parse_tick(source_tick), source_port)
        self.dest = Endpoint(Tick.parse_tick(dest_tick), dest_port)
        
