# Copyright (C) 2015 Stefan C. Mueller

import ast
from pydron.translation import saneitizer, utils, naming, builtins
from pydron.dataflow import graph, tasks
from pydron.dataflow import utils as dataflowutils
import inspect
import enum
import logging
import sys
import importlib
logger = logging.getLogger(__name__)

class UnassignedLocalStrategy(enum.Enum):
    FAIL = 1,
    MAKE_GRAPH_INPUT = 2

class GraphFactory(object):
    """
    Creates :class:`graph.Graph` instances. This class offers some handy functions
    but mostly its job is to keep track of the variable to :class:`OutPort` mapping.
    """
    
    def __init__(self, unassinged_local_strategy=UnassignedLocalStrategy.FAIL):
        self._unassinged_local_strategy = unassinged_local_strategy
        self._graph = graph.Graph()
        self._next_tick = graph.START_TICK + 1
        
        # known local variables.
        # maps variable name to Endpoint.
        self._varmap = {}
        
        # Variablenames that were assigned.
        # not all in varmap were assigned, see `unassinged_local_strategy`.
        self._assigned_vars = set()
    
    def exec_task(self, task, inputs=[], autoconnect=False, quick=False, syncpoint=False, nosend_ports=None):
        """
        Adds a task to the graph. 
        
        :param inputs: List of `(source, in_port)` tuples. 
        
        :param autoconnect: If `true` all inputs that don't start with a `$` are
         automatically read from variables and all ouputs with the same criteria
         assigned to variables.
          
        :returns: tick
        """
        
        for subgraph in task.subgraphs():
            syncpoint |= dataflowutils.contains_sideeffects(subgraph)
        
        tick = self._next_tick
        self._next_tick += 1
        properties = {}
        if quick:
            properties["quick"] = True
        if syncpoint:
            properties["syncpoint"] = True
        if nosend_ports:
            properties["nosend_ports"] = nosend_ports
        self._graph.add_task(tick, task, properties)
        
        for source, in_port in inputs:
            self._graph.connect(source, graph.Endpoint(tick, in_port))
            
        if autoconnect:
            for var in task.input_ports():
                if not var.startswith("$"):
                    source = self.read_variable(var)
                    self._graph.connect(source, graph.Endpoint(tick, var))
                    
            for var in task.output_ports():
                if not var.startswith("$"):
                    source = graph.Endpoint(tick, var)
                    self.assign_variable(var, source)
        
        return tick
                
    def exec_expr(self, task, inputs={}, quick=False, syncpoint=False, nosend_ports=None):
        """
        Same as :meth:`exec_task` but returns an instance of :class:`ValueNode` for
        a port named `value`.
        """
        tick = self.exec_task(task, inputs=inputs, quick=quick, syncpoint=syncpoint, nosend_ports=nosend_ports)
        return graph.Endpoint(tick, "value")
    
    def read_variable(self, var):
        """
        Returns the :class:`graph.Endpoint` that represents the current content
        of a given variable.
        """
        assert isinstance(var, str)
        if var not in self._varmap:
            if self._unassinged_local_strategy == UnassignedLocalStrategy.FAIL:
                raise ValueError("Unassigned local variable: %s" % repr(var))
            elif self._unassinged_local_strategy == UnassignedLocalStrategy.MAKE_GRAPH_INPUT:
                self._varmap[var] = self.graph_input(var)
            else:
                raise ValueError("unsupported strategy: %s" % self._unassinged_local_strategy)
            
        return self._varmap[var]
    
    def assign_variable(self, var, endpoint):
        """
        Binds the given :class:`graph.Endpoint` to the given variable name. Furture calls
        to :meth:`read_variable` will return this port.
        """
        assert isinstance(var, str)
        self._varmap[var] = endpoint
        self.set_nice_name(endpoint, var)
        self._assigned_vars.add(var)
        
    def graph_input(self, port):
        """
        Declares an input with name `port` of the graph. Returns an instance
        of :class:`graph.Endpoint`.
        """
        return graph.Endpoint(graph.START_TICK, port)
    
    def graph_output(self, source, port):
        """
        Declares an output with name `port`.
        
        This creates an output port `port` on `FINAL_TICK` connected to the given valuenode.
        """
        self._graph.connect(source, graph.Endpoint(graph.FINAL_TICK, port))
        self.set_nice_name(source, port)

    def make_assigned_vars_outputs(self):
        """
        For each variable that was assigned, make a graph output with the variable name
        as port name. This first removes all graph outputs that don't start with `$`.
        """
        for source, dest in self._graph.get_in_connections(graph.FINAL_TICK):
            if not dest.port.startswith("$"):
                self._graph.disconnect(source, dest)
            
        for var in self._assigned_vars:
            source = self._varmap[var]
            self.graph_output(source, var)

    def get_graph(self):
        return self._graph
    
    def set_nice_name(self, endpoint, name):
        """
        Gives an out-port a name for debugging purposes.
        The names of output ports are often as simple as "value". The "nicenames" property
        of a task is used to store a nicer name for the port, to ease debugging.
        """
        if endpoint.tick == graph.START_TICK:
            return
        props = self._graph.get_task_properties(endpoint.tick)
        nicenames = props.get("_nicenames", {})
        nicenames = dict(nicenames)
        nicenames[endpoint.port] = name
        self._graph.set_task_property(endpoint.tick, "_nicenames", nicenames)

class Translator(ast.NodeVisitor):
    
    def __init__(self, id_factory, scheduler, module_name):
        """
        :param scheduler: Scheduler to be used by translated functions.
        """
        self.id_factory = id_factory
        self.scheduler = scheduler
        self.module_name = module_name
        self.factory_stack = []
        
        
    def visit_Module(self, node):
        """
        The module visitor is a bit special, it returns
        the module's graph. We'll extract the `FunctionDefTask`
        from it since we only translate functions.
        """
        factory = GraphFactory()
        self.factory_stack.append(factory)
        for stmt in node.body:
            self.visit(stmt)
        self.factory_stack.pop()
        return factory.get_graph()


    def visit_FunctionDef(self, node):
        assert not node.decorator_list, "Not supported"
        
        # Default values become inputs to the task
        defaults = {"default_%s" % i:self.visit(d) for i, d in enumerate(node.args.defaults)}
    
        factory = GraphFactory()
        
        # Prepare the inputs of the body-graph
        for arg in node.args.args:
            vn = factory.graph_input(arg.id)
            factory.assign_variable(arg.id, vn)
        if node.args.vararg:
            vn = factory.graph_input(node.args.vararg)
            factory.assign_variable(node.args.vararg, vn)
        if node.args.kwarg: 
            vn = factory.graph_input(node.args.kwarg)
            factory.assign_variable(node.args.kwarg, vn)
    
        # lets build the body graph.
        self.factory_stack.append(factory)
        for stmt in node.body:
            self.visit(stmt)
        self.factory_stack.pop()
        
        body_graph = factory.get_graph()
        
        # some sanity checks
        graph_outputs = list(body_graph.get_in_connections(graph.FINAL_TICK))
        if len(graph_outputs) != 1:
            raise ValueError("Function graph invalid. Expected exactly one output:%s" % `graph_outputs`)
        _, graph_output_dest = graph_outputs[0]
        if graph_output_dest.port != "retval":
            raise ValueError("Function graph invalid. Missing return value:%s" % `graph_outputs`)
        
        
        task = tasks.FunctionDefTask(scheduler=self.scheduler, 
                                     name=node.name,
                                     graph=body_graph, 
                                     args=[arg.id for arg in node.args.args], 
                                     vararg = node.args.vararg, 
                                     kwarg = node.args.kwarg, 
                                     num_defaults = len(defaults))
        
        tick = self.factory_stack[-1].exec_task(task, inputs=defaults, quick=True, syncpoint=False)
        self.factory_stack[-1].assign_variable(node.name, graph.Endpoint(tick, "function"))
        
    def visit_ClassDef(self, node):
        raise ValueError("not supported")
    
    def visit_Delete(self, node):
        raise ValueError("not supported")
    
    def visit_Assign(self, node):
        target = node.targets[0]
        
        if (isinstance(node.value, ast.Call) and 
            isinstance(node.value.func, ast.Name) and 
            node.value.func.id == "__pydron_next__"):
            
            call =  node.value
            assert len(call.args) == 1
            assert len(call.keywords) == 0
            assert call.starargs is None
            assert call.kwargs is None
            assert isinstance(target, ast.Tuple)
            assert len(target.elts) == 2
            assert isinstance(target.elts[0], ast.Name)
            assert isinstance(target.elts[1], ast.Name)
             
            iterator = self.visit(call.args[0])
            
            tick = self.factory_stack[-1].exec_task(tasks.NextTask(), 
                    [(iterator, "iterator")], 
                    quick=True, syncpoint=False, nosend_ports={"iterator"})
            
            self.factory_stack[-1].assign_variable(target.elts[0].id, graph.Endpoint(tick, "value"))
            self.factory_stack[-1].assign_variable(target.elts[1].id, graph.Endpoint(tick, "iterator"))
            return 

        value = self.visit(node.value)
        
        if isinstance(target, ast.Name):
            self.factory_stack[-1].assign_variable(target.id, value)
            
        elif isinstance(target, ast.Attribute):
            obj = self.visit(target.value)
            attr = target.attr
            
            self.factory_stack[-1].exec_task(tasks.AttrAssign(attr), 
                    [(obj, "object"), (value, "value")], 
                    quick=True, syncpoint=True)

        elif isinstance(target, ast.Subscript):
            obj = self.visit(target.value)
            assert isinstance(target.slice, ast.Index)
            subscript = self.visit(target.slice.value)
            
            self.factory_stack[-1].exec_task(tasks.SubscriptAssign(),
                    [(obj, "object"), (subscript, "slice"), (value, "value")], 
                    quick=True, syncpoint=True)
            
        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            count = len(target.elts)
            tick = self.factory_stack[-1].exec_task(tasks.UnpackTask(count), [(value, 'value')], quick=True)
            
            for i in range(count):
                assert isinstance(target.elts[i], ast.Name)
                ep = graph.Endpoint(tick, str(i))
                self.factory_stack[-1].assign_variable(target.elts[i].id, ep)
                
        else:
            raise ValueError("not supported")
        
    def visit_AugAssign(self, node):
        target = node.target
        value = self.visit(node.value)
        
        if isinstance(target, ast.Name):
            
            target_ep = self.factory_stack[-1].read_variable(target.id)
            
            newtarget = self.factory_stack[-1].exec_expr(tasks.AugAssignTask(node.op), [
                    (target_ep, "target"),
                    (value, "value")
                ], quick=True, syncpoint=True)
            self.factory_stack[-1].assign_variable(target.id, newtarget)
    
    
        elif isinstance(target, ast.Attribute):
            
            obj = self.visit(target.value)
            
            task = tasks.AugAttrAssignTask(node.op, target.attr)
            
            self.factory_stack[-1].exec_task(task, inputs=[
                 (obj, "target"), (value, "value")
            ], quick=True, syncpoint=True)
    
        elif isinstance(target, ast.Subscript):
            
            obj = self.visit(target.value)
            assert isinstance(target.slice, ast.Index)
            index = self.visit(target.slice.value)
            
            task = tasks.AugSubscriptAssignTask(node.op)
            
            self.factory_stack[-1].exec_task(task, inputs=[
                 (obj, "target"), (index, "slice"), (value, "value")
            ], quick=True, syncpoint=True)
            
        else:
            raise ValueError("not supported")
       
    
    def visit_Print(self, node):
        raise ValueError("not supported")
    
    def visit_For(self, node):
        
        # Get rid of `break` but remember the AST expression that tells us when it executes
        body_statements, break_condition = _extract_break(node.body)
        
        # Factory for the body
        body_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
        
        # Make the target an input to the body graph
        target_endpoint = body_factory.graph_input("$target")
        body_factory.assign_variable(node.target.id, target_endpoint)
        
        # Create the body graph. This still lacks the tail-recursive task, though.
        self.factory_stack.append(body_factory)
        for stmt in body_statements:
            self.visit(stmt)
        if break_condition:
            breaked = self.visit(break_condition)
        else:
            breaked = None
        self.factory_stack.pop()
        body_factory.make_assigned_vars_outputs()
        body_graph = body_factory.get_graph()
        
        # Create the graph for orelse.
        orelse_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
        self.factory_stack.append(orelse_factory)
        for stmt in node.orelse:
            self.visit(stmt)
        self.factory_stack.pop()
        orelse_factory.make_assigned_vars_outputs()
        orelse_graph = orelse_factory.get_graph()
        
        # We create the tail-recursive loop task. It stores the incomplete body graph
        # but that is ok, we'll change that graph in-place.
        inner_fortask = tasks.ForTask(True, breaked is not None, body_graph, orelse_graph)
        
        # The iterator must become an input to the body graph and passed on to the
        # tail-recursive loop task for the next iterations.
        iterator_endpoint = body_factory.graph_input("$iterator")
        inner_task_inputs = [(iterator_endpoint, "$iterator")]
        if breaked:
            inner_task_inputs.append((breaked, "$breaked"))

        # Add the nested loop task
        body_factory.exec_task(inner_fortask, inputs=inner_task_inputs, autoconnect=True)
        
        # we messed with the body graph since we did this the last time, we have to redo this.
        body_factory.make_assigned_vars_outputs()
        
        # -- body and orelse graphs are complete --
        
        # -- add the task for the complete loop to the current graph --
        
        # Even before the loop, get an iterator from the iterable.
        iterable = self.visit(node.iter)
        iterator = self.factory_stack[-1].exec_expr(tasks.IterTask(), inputs=[(iterable, 'iterable')], quick=True)
        
        # Finally we can add the loop task.
        fortask = tasks.ForTask(False, False, body_graph, orelse_graph)
        self.factory_stack[-1].exec_task(fortask, inputs=
                    [(iterator, "$iterator")],
                    autoconnect=True)
        
    def visit_While(self, node):
        
        # Get rid of `break` but remember the AST expression that tells us when it executes
        body_statements, break_condition = _extract_break(node.body)
        
        # Factory for the body
        body_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
                
        # Create the body graph. This still lacks the tail-recursive task, though.
        self.factory_stack.append(body_factory)
        for stmt in body_statements:
            self.visit(stmt)
            
        # Visit break
        if break_condition:
            breaked = self.visit(break_condition)
        else:
            breaked = None
            
        # Condition for next iteration
        inner_condition = self.visit(node.test)
            
        self.factory_stack.pop()
        body_factory.make_assigned_vars_outputs()
        body_graph = body_factory.get_graph()
        
        # Create the graph for orelse.
        orelse_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
        self.factory_stack.append(orelse_factory)
        for stmt in node.orelse:
            self.visit(stmt)
        self.factory_stack.pop()
        orelse_factory.make_assigned_vars_outputs()
        orelse_graph = orelse_factory.get_graph()
        
        # We create the tail-recursive loop task. It stores the incomplete body graph
        # but that is ok, we'll change that graph in-place.
        inner_task = tasks.WhileTask(True, breaked is not None, body_graph, orelse_graph)
        

        inner_task_inputs = [(inner_condition, "$test")]
        if breaked:
            inner_task_inputs.append((breaked, "$breaked"))

        # Add the nested loop task
        body_factory.exec_task(inner_task, inputs=inner_task_inputs, autoconnect=True)
        
        # we messed with the body graph since we did this the last time, we have to redo this.
        body_factory.make_assigned_vars_outputs()
        
        # -- body and orelse graphs are complete --
        
        # -- add the task for the complete loop to the current graph --
        
        # Even before the loop, get an iterator from the iterable.
        test = self.visit(node.test)
        
        # Finally we can add the loop task.
        whiletask = tasks.WhileTask(False, False, body_graph, orelse_graph)
        self.factory_stack[-1].exec_task(whiletask, inputs=
                    [(test, "$test")],
                    autoconnect=True)

    def visit_If(self, node):    
        test = self.visit(node.test)
        
        body_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
        self.factory_stack.append(body_factory)
        for stmt in node.body:
            self.visit(stmt)
        self.factory_stack.pop()
        body_factory.make_assigned_vars_outputs()
        
        orelse_factory = GraphFactory(unassinged_local_strategy=UnassignedLocalStrategy.MAKE_GRAPH_INPUT)
        self.factory_stack.append(orelse_factory)
        for stmt in node.orelse:
            self.visit(stmt)
        self.factory_stack.pop()
        orelse_factory.make_assigned_vars_outputs()
        
        task = tasks.IfTask(body_factory.get_graph(), orelse_factory.get_graph())
        tick = self.factory_stack[-1].exec_task(task, inputs=[(test, '$test')])
        
        for in_port in task.input_ports():
            if in_port.startswith("$"):
                continue
            source = self.factory_stack[-1].read_variable(in_port)
            dest = graph.Endpoint(tick, in_port)
            self.factory_stack[-1].get_graph().connect(source, dest)
            
        for out_port in task.output_ports():
            if out_port.startswith("$"):
                continue
            source = graph.Endpoint(tick, out_port)
            self.factory_stack[-1].assign_variable(out_port, source)
        
    
    def visit_With(self, node):
        raise ValueError("not supported")
    
    def visit_Raise(self, node):
        if any(n is None for n in [node.type, node.inst, node.tback]):
            noneval = self.factory_stack[-1].exec_expr(tasks.ConstTask(None), quick=True)
            
        def default_to_none(node):
            if node is None:
                return noneval
            else:
                return self.visit(node)
            
        t = default_to_none(node.type)
        i = default_to_none(node.inst)
        tb = default_to_none(node.tback)
        
        self.factory_stack[-1].exec_task(tasks.RaiseTask(), inputs=[(t, "type"), (i, "inst"), (tb, "tback")], quick=True)
    
    def visit_TryExcept(self, node):
        raise ValueError("not supported")
    
    def visit_TryFinally(self, node):
        raise ValueError("not supported")
    
    def visit_Assert(self, node):
        raise ValueError("not supported")
    
    def visit_Import(self, node):
        raise ValueError("not supported")
    
    def visit_ImportFrom(self, node):
        raise ValueError("not supported")
    
    def visit_Exec(self, node):
        raise ValueError("not supported")
    
    def visit_Global(self, node):
        raise ValueError("not supported")
    
    def visit_Expr(self, node):
        self.generic_visit(node)
        
    def visit_Pass(self, node):
        pass
    
    def visit_Break(self, node):
        raise ValueError("not supported")
    
    def visit_Continue(self, node):
        raise ValueError("not supported")
    
    def visit_BoolOp(self, node):
        raise ValueError("not supported")
    
    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return self.factory_stack[-1].exec_expr(tasks.BinOpTask(node.op), 
                                                [(left, "left"), (right, "right")],
                                                quick=True, syncpoint=False)
        
    def visit_UnaryOp(self, node):
        value = self.visit(node.operand)
        return self.factory_stack[-1].exec_expr(tasks.UnaryOpTask(node.op), 
                                                [(value, "value")],
                                                quick=True, syncpoint=False)
        
    def visit_Lambda(self, node):
        raise ValueError("not supported")
    
    def visit_IfExp(self, node):
        raise ValueError("not supported")
    
    def visit_Dict(self, node):
        assert len(node.keys) == len(node.values)
        
        count = len(node.keys)
        
        inputs = []
        for i in range(count):
            k = self.visit(node.keys[i])
            v = self.visit(node.values[i])
            inputs.append((k, "key_%s" % i))
            inputs.append((v, "value_%s" % i))
            
        return self.factory_stack[-1].exec_expr(tasks.DictTask(count), 
                                                inputs,
                                                quick=True, syncpoint=False)  
        
    def visit_Set(self, node):
        count = len(node.elts)
        
        inputs = []
        for i in range(count):
            v = self.visit(node.elts[i])
            inputs.append((v, "value_%s" % i))
            
        return self.factory_stack[-1].exec_expr(tasks.SetTask(count), 
                                                inputs,
                                                quick=True, syncpoint=False)  
        
    def visit_ListComp(self, node):
        raise ValueError("not supported")
    
    def visit_SetComp(self, node):
        raise ValueError("not supported")
    
    def visit_DictComp(self, node):
        raise ValueError("not supported")
    
    def visit_GeneratorExp(self, node):
        raise ValueError("not supported")
    
    def visit_Yield(self, node):
        raise ValueError("Yield statements are not supported by Pydron. These can result from generator expressions.")
    
    def visit_Compare(self, node):
        assert len(node.comparators) == 1
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        op = node.ops[0]
        
        return self.factory_stack[-1].exec_expr(tasks.BinOpTask(op), 
                                                [(left, "left"), (right, "right")],
                                                quick=True, syncpoint=False)
        
    def visit_Call(self, node):
        
        def handle_builtin(num_args, function, syncpoint, nosend=False):
            assert len(node.args) == num_args
            assert len(node.keywords) == 0
            assert node.starargs is None
            assert node.kwargs is None
            task = tasks.BuiltinCallTask(function, num_args)
            inputs = [(self.visit(node.args[i]), "arg%s" % i) for i in range(num_args)]
            if nosend:
                nosend_ports = {"value"}
            else:
                nosend_ports = None
            return self.factory_stack[-1].exec_expr(task,
                                                    inputs,
                                                    quick=True, syncpoint=syncpoint, nosend_ports=nosend_ports)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_unbound_check__":
            assert len(node.args) == 1
            assert len(node.keywords) == 0
            assert node.starargs is None
            assert node.kwargs is None
            return self.visit(node.args[0])
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_unbound_unchecked__":
            return handle_builtin(1, builtins.__pydron_unbound_unchecked__, syncpoint=False)
            
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_locals__":
            return handle_builtin(1, builtins.__pydron_locals__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_new_cell__":
            return handle_builtin(1, builtins.__pydron_new_cell__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_wrap_closure__":
            return handle_builtin(2, builtins.__pydron_wrap_closure__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_assign_global__":
            assert len(node.args) == 2
            assert len(node.keywords) == 0
            assert node.starargs is None
            assert node.kwargs is None
            task = tasks.AssignGlobal(self.module_name)
            inputs = [(self.visit(node.args[0]), "var"),
                      (self.visit(node.args[1]), "value")]
            return self.factory_stack[-1].exec_expr(task,
                                                    inputs,
                                                    quick=True, syncpoint=True)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_read_global__":
            assert len(node.args) == 1
            assert len(node.keywords) == 0
            assert node.starargs is None
            assert node.kwargs is None
            task = tasks.ReadGlobal(self.module_name)
            inputs = [(self.visit(node.args[0]), "var")]
            return self.factory_stack[-1].exec_expr(task,
                                                    inputs,
                                                    quick=True, syncpoint=False)
            
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_defaults__":
            return handle_builtin(3, builtins.__pydron_defaults__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_print__":
            return handle_builtin(3, builtins.__pydron_print__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_exec__":
            return handle_builtin(3, builtins.__pydron_exec__, syncpoint=True)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_max__":
            return handle_builtin(2, builtins.__pydron_max__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_iter__":
            return handle_builtin(1, builtins.__pydron_iter__, syncpoint=False, nosend=True)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_hasnext__":
            return handle_builtin(1, builtins.__pydron_hasnext__, syncpoint=False)
        
        if isinstance(node.func, ast.Name) and node.func.id == "__pydron_next__":
            raise ValueError("__pydron_next__ can only be used with a tuple assignment.")

        numargs = len(node.args)
        keywords = [k.arg for k in node.keywords]
        
        task = tasks.CallTask(numargs, keywords, node.starargs is not None, node.kwargs is not None)
        
        inputs = [(self.visit(node.func), "func")]
        
        for i in range(numargs):
            inputs.append((self.visit(node.args[i]), "arg_%s" % i))
            
        for i in range(len(keywords)):
            inputs.append((self.visit(node.keywords[i].value), "karg_%s" % i))
        
        if node.starargs is not None:
            inputs.append((self.visit(node.starargs), "starargs"))
        
        if node.kwargs is not None:
            inputs.append((self.visit(node.kwargs), "kwargs"))
            
        return self.factory_stack[-1].exec_expr(task,
                                                inputs,
                                                quick=False, syncpoint=True)
        
    def visit_Repr(self, node):
        return self.factory_stack[-1].exec_expr(tasks.ReprTask,
                                                [(self.visit(node.value), "value")],
                                                quick=True, syncpoint=False)
        
    def visit_Num(self, node):
        return self.factory_stack[-1].exec_expr(tasks.ConstTask(node.n), quick=True, syncpoint=False)
    
    def visit_Str(self, node):
        return self.factory_stack[-1].exec_expr(tasks.ConstTask(node.s), quick=True, syncpoint=False)
    
    def visit_Attribute(self, node):
        assert isinstance(node.ctx, ast.Load)
        
        return self.factory_stack[-1].exec_expr(tasks.AttributeTask(node.attr), 
                                                [(self.visit(node.value), "object")],
                                                quick=True, syncpoint=False)
        
    def visit_Subscript(self, node):
        assert isinstance(node.ctx, ast.Load)
        assert isinstance(node.slice, ast.Index)
        
        obj = self.visit(node.value)
        sl = self.visit(node.slice.value)
        
        return self.factory_stack[-1].exec_expr(tasks.SubscriptTask(), 
                                                [(obj, "object"),
                                                 (sl, "slice")],
                                                quick=True, syncpoint=False)
        
    def visit_Name(self, node):
        assert not isinstance(node, ast.Store)
        if node.id == "None":
            return self.factory_stack[-1].exec_expr(tasks.ConstTask(None), quick=True, syncpoint=False)
        elif node.id == "True":
            return self.factory_stack[-1].exec_expr(tasks.ConstTask(True), quick=True, syncpoint=False)
        elif node.id == "False":
            return self.factory_stack[-1].exec_expr(tasks.ConstTask(False), quick=True, syncpoint=False)
        elif node.id == "__pydron_unbound__":
            return self.factory_stack[-1].exec_expr(tasks.ConstTask(builtins.__pydron_unbound__), quick=True, syncpoint=False)
        elif node.id == "__pydron_unbound_nocheck__":
            return self.factory_stack[-1].exec_expr(tasks.ConstTask(builtins.__pydron_unbound_nocheck__), quick=True, syncpoint=False)
        elif node.id.startswith("__pydron"):
            raise ValueError("Unrecognized builtin: %r" % node.id)
        else:
            return self.factory_stack[-1].read_variable(node.id)
        
    def visit_List(self, node):
        assert not isinstance(node, ast.Store)
        count = len(node.elts)
        
        inputs = []
        for i in range(count):
            v = self.visit(node.elts[i])
            inputs.append((v, "value_%s" % i))
            
        return self.factory_stack[-1].exec_expr(tasks.ListTask(count), 
                                                inputs,
                                                quick=True, syncpoint=False)  
        
    def visit_Tuple(self, node):
        assert not isinstance(node, ast.Store)
        count = len(node.elts)
        
        inputs = []
        for i in range(count):
            v = self.visit(node.elts[i])
            inputs.append((v, "value_%s" % i))
            
        return self.factory_stack[-1].exec_expr(tasks.TupleTask(count), 
                                                inputs,
                                                quick=True, syncpoint=False) 
        
    def visit_Return(self, node):
        vn = self.visit(node.value)
        self.factory_stack[-1].graph_output(vn, "retval")
    


        

def translate_function(function, scheduler, saneitize=True):
    """
    Translates a function into a :class:`tasks.ScheduledCallable`.
    """
    
    def main_workaround(module_name):
        """
        If the function is inside __main__ we have problem
        since the workers will have a different module called
        __main__.
        So we make a best-effort attemt to find if __main__
        is also reachable as a module.
        """
        if module_name != "__main__":
            return module_name # we are fine.
        
        # See if we can find a sys.path that matches the location of __main__
        main_file = getattr(sys.modules["__main__"], "__file__",  "")
        candidates = {path for path in sys.path if main_file.startswith(path)}
        candidates = sorted(candidates, key=len)
        for candidate in candidates:
            
            # Try to create the absolute module name from the filename only.
            module_name = main_file[len(candidate):]
            if module_name.endswith(".py"):
                module_name = module_name[:-3]
            if module_name.endswith(".pyc"):
                module_name = module_name[:-4]
            module_name = module_name.replace("/", ".")
            module_name = module_name.replace("\\", ".")
            while module_name.startswith("."):
                module_name = module_name[1:]
                
            # Check if it actually works.
            try:
                module = importlib.import_module(module_name)
                return module.__name__
            except ImportError:
                pass
            
        # we were unlucky.
        raise ValueError("The functions in the __main__ module cannot be translated.")
    
    source = inspect.getsourcelines(function)
    source = "".join(source[0])
    
    logger.info("Translating: \n%s" % source)
    
    node = ast.parse(utils.unindent(source))
    
    # Remove decorators
    
    # TODO handle decorators properly
    assert len(node.body) == 1
    funcdef = node.body[0]
    assert isinstance(funcdef, ast.FunctionDef)
    funcdef.decorator_list = []
    
    if len(funcdef.args.defaults) != 0:
        # TODO add support
        raise ValueError("Cannot translate %f: @schedule does not support functions with default arguments")

    id_factory = naming.UniqueIdentifierFactory()

    if saneitize:
        makesane = saneitizer.Saneitizer()
        node = makesane.process(node, id_factory)
        
    module_name = getattr(function, "__module__", None)
    if not module_name:
        raise ValueError("Cannot translate %f: The module in which it is defined is unknown.")
    module_name = main_workaround(module_name)
    
    import astor
    logger.info("Preprocessed source:\n%s" % astor.to_source(node))

    translator = Translator(id_factory, scheduler, module_name)
    graph = translator.visit(node)
    
    def find_FunctionDefTask(graph):
        for tick in graph.get_all_ticks():
            task = graph.get_task(tick)
            if isinstance(task, tasks.FunctionDefTask):
                return task
        raise ValueError("No function was translated.")
    
    funcdeftask = find_FunctionDefTask(graph)
    
    defaults = function.__defaults__
    if not defaults:
        defaults = tuple()
    
    if funcdeftask.num_defaults != len(defaults):
        raise ValueError("Number of default arguments doesn't match.")
    
    if function.__closure__:
        raise ValueError("Translating closures currently not supported.")
    
    inputs = {"default_%s"%i:v for i, v in enumerate(defaults)}
    scheduled_callable = funcdeftask.evaluate(inputs)['function']
    return scheduled_callable
    
    
def _extract_break(statements):
    """
    Search for the following pattern:
    Last statement is an `if` without an `orelse` and
    a single `break` statement in the body.
    
    Returns all statements without this `if` and the
    expression for the `if` condition. If no such
    `if` is found, all statements are returned and the
    expression is None.
    """
    
    found_break = False
    if statements:
        ifstmt = statements[-1]
        if isinstance(ifstmt, ast.If):
            if not ifstmt.orelse:
                ifbody = ifstmt.body
                if len(ifbody) == 1:
                    if isinstance(ifbody[0], ast.Break):
                        found_break = True
                        
    if found_break:
        return statements[:-1], ifstmt.test
    else:
        return statements, None