# Copyright (C) 2015 Stefan C. Mueller
import importlib
import logging
import __builtin__
from pydron import whitelist
from pydron.dataflow import graph, refine, utils
from pydron.translation import builtins
import sys

logger = logging.getLogger(__name__)

class ScheduledCallable(object):
    """
    Callable that we return when translating a function into a data-flow graph.
    Invoking it will run the scheduler.
    """
    
    def __init__(self, scheduler, name, graph, args, vararg, kwarg, default_values):
        self.scheduler = scheduler
        self.graph = graph
        self.args = args
        self.vararg = vararg
        self.kwarg = kwarg
        self.default_values = default_values
        
        self.__doc__ = None
        self.func_doc = None
        
        self.__name__ = name
        self.func_name = name
        self.__defaults__ = default_values
        self.func_defaults = default_values
        
    
    def __call__(self, *args, **kwargs):
        """
        Execute the call by letting the scheduler run the graph.
        """
        
        def calling_convention(call_args, call_kwargs):
            """
            Takes the positional and keyword arguments of the call
            and maps them to the parameters of the called method.
            This is a bit complicated because the callee might
            have `*args` and `**kwargs` as well as default values for
            parameters.
            
            Returns `args`, `vararg`, and `kwarg` for the callee.
            The first has the same length as `self.args`.
            The later two are `None` if `self.vararg` or `self.kwarg`
            are `None`
            """
            
            # Positional arguments of the callee.
            # Keep track for which we know the value already.
            # We use a separate list since `None` is a valid argument.
            callee_args = [None] * len(self.args)
            callee_args_marker = [False] * len(self.args)
            
            # Match positional arguments of the call to positional
            # parameters of the callee.
            formal_matches = min(len(call_args), len(self.args))
            for i in range(formal_matches):
                callee_args[i] = args[i]
                callee_args_marker[i] = True
                
            # Any positional arguments of the call that doesn't
            # match a positional parameter o the callee goes
            # into `*args` if the callee has that.
            remaining_args = len(call_args) - formal_matches
            if self.vararg:
                if remaining_args:
                    callee_vararg = tuple(call_args[-remaining_args:])
                else:
                    callee_vararg = tuple()
            else:
                if remaining_args:
                    raise TypeError("Passed %s arguments, callee expects %s" % (len(call_args), len(self.args)))
                else:
                    callee_vararg = None
                    
            # Fill keyword arguments of the call to positional arguments
            # of the callee.
            # All that we don't find an argument for are going into `**kwargs`
            # of the callee...
            callee_kwarg = {}
            for key, val in call_kwargs.iteritems():
                try:
                    i = self.args.index(key)
                except ValueError:
                    callee_kwarg[key] = val
                else:
                    if callee_args_marker[i]:
                        raise TypeError("Parameter %s already assigned." % key)
                    else:
                        callee_args[i] = val
                        callee_args_marker[i] = True
                        
            # ... if callee has `**kwargs`.
            if not self.kwarg:
                if callee_kwarg:
                    raise TypeError("No parameter named %s" % next(iter(callee_kwarg)))
                else:
                    callee_kwarg = None
            
            # Positional arguments of the callee for which we still miss
            # the value are filled with the default value (if one exists).
            num_args_without_default = len(self.args) - len(self.default_values)
            for i in range(len(self.args)):
                if not callee_args_marker[i]:
                    if i >= num_args_without_default:
                        val = self.default_values[num_args_without_default + i]
                        callee_args[i] = val
                        callee_args_marker[i] = True
                    else:
                        raise TypeError("Passed %s arguments, callee expects %s" % (len(call_args), num_args_without_default))
                    
            
            return callee_args, callee_vararg, callee_kwarg
    
        callee_args, callee_vararg, callee_kwarg = calling_convention(args, kwargs)
        
        inputs = {}
        for i in range(len(self.args)):
            inputs[self.args[i]] = callee_args[i]
        if self.vararg:
            inputs[self.vararg] = callee_vararg
        if self.kwarg:
            inputs[self.kwarg] = callee_kwarg
        
        outputs = self.scheduler.execute_blocking(self.graph, inputs)
        
        retval = outputs['retval']
        return retval
    
    
class AbstractTask(object):
    
    # Input ports required for refining.
    # We won't refine if the attribute is missing.
    #refiner_ports = set()
    
    # Maps input port to a function that takes one
    # argument. If the attribute exists then
    # this function is invoked with the value
    # and the return value is passed to `refine`
    # instead of the actual value.
    # The function must be defined in a module
    # so that it can be pickled.
    # The idea of this is to reduce the amount
    # of data that has to be transferred back
    # to the scheduler for refinement.
    #refiner_reducer = {}
    
    def input_ports(self):
        raise NotImplementedError("abstract")
    
    def output_ports(self):
        raise NotImplementedError("abstract")
    
    def subgraphs(self):
        return tuple()
    
    def evaluate(self, inputs):
        raise NotImplementedError("abstract")
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return not self == other
    def __hash__(self):
        return 1
    
        
class ConstTask(AbstractTask):
    """
    Evaluates to a constant value.
    """
    
    def __init__(self, value):
        self.value = value
    
    def input_ports(self):
        return set()
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {'value': self.value}
    
    def __repr__(self):
        return "ConstTask(" + repr(self.value) + ")"
    
    def __eq__(self, other):
        return self.value == other.value
    

class FunctionDefTask(AbstractTask):
    """
    Evaluates to a `ScheduledCallable`.
    """
    
    def __init__(self, scheduler, name, args, vararg, kwarg, num_defaults, graph):
        self.scheduler = scheduler 
        self.name = name
        self.graph = graph
        self.args = args
        self.vararg = vararg
        self.kwarg = kwarg
        self.num_defaults = num_defaults
        
    def input_ports(self):
        return {"default_%s" % i for i in range(self.num_defaults)}
    
    def output_ports(self):
        return {"function"}
        
    def evaluate(self, inputs):
        assert set(inputs.keys()) == self.input_ports()
        
        default_values = [inputs["default_%s"%i] for i in range(self.num_defaults)]
        
        c = ScheduledCallable(scheduler=self.scheduler, 
                          name=self.name,
                          graph=self.graph,
                          args=self.args,
                          vararg=self.vararg,
                          kwarg=self.kwarg,
                          default_values=default_values)
        return {'function':c}
    
    def __repr__(self):
        return "FunctionDefTask({scheduler}, {name}, {args}, {vararg}, {kwarg}, {num_defaults}, {graph})".format(
            scheduler=repr(self.scheduler),
            name=repr(self.name),
            graph=repr(self.graph),
            args=repr(self.args),
            vararg=repr(self.vararg),
            kwarg=repr(self.kwarg),
            num_defaults=repr(self.num_defaults)
        )
    
        
class IfTask(AbstractTask):
    
    refiner_ports = {"$test"}
    refiner_reducer = {"$test": bool}
    
    def __init__(self, body_graph, orelse_graph):
        self.body_graph = body_graph
        self.orelse_graph = orelse_graph
    
    def input_ports(self):
        body_inputs = {source.port for source, _ in  self.body_graph.get_out_connections(graph.START_TICK)}
        orelse_inputs = {source.port for source, _ in  self.orelse_graph.get_out_connections(graph.START_TICK)}
        
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}

        potentially_unassigned = body_outputs ^ orelse_outputs
        
        return body_inputs | orelse_inputs | potentially_unassigned | {"$test"}
        
    def output_ports(self):
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}
        
        return body_outputs | orelse_outputs
    
    def subgraphs(self):
        return (self.body_graph, self.orelse_graph)
    
    def evaluate(self, inputs):
        raise ValueError("replaced by subgraph")
    
    def refine(self, g, tick, known_inputs):
        if known_inputs["$test"]:
            subgraph = self.body_graph
        else:
            subgraph = self.orelse_graph
            
        refine.replace_task(g, tick, subgraph)
    
    def __repr__(self):
        return "IfTask(%s, %s)" % (self.body_graph, self.orelse_graph)

class IterTask(AbstractTask):
    def __init__(self):
        pass
    
    def input_ports(self):
        return {"iterable"}
    def output_ports(self):
        return {"value"}
    def evaluate(self, inputs):
        iterable = inputs["iterable"]
        iterator = iter(iterable)
        return {"value":iterator}
    
    def __repr__(self):
        return "IterTask()"

class ForTask(AbstractTask):
    
    def __init__(self, is_tail, has_breaked_input, body_graph, orelse_graph):
        """
        :param is_tail: If `False` this task represents the complete loop. If `True`
          it represents the reminder of the loop. The tail has `$breaed` as an
          additional input to know if the previous iteration aborted with `break`.
          There are also differences in the tick calculation when unrolling.
          
        :param has_breaked_input: If there is a `$breaked` input from a potential
          `break` statement during the previous iteration. 
        """
        self.is_tail = is_tail
        self.has_breaked_input = has_breaked_input
        self.body_graph = body_graph
        self.orelse_graph = orelse_graph
        
        if self.has_breaked_input:
            self.refiner_ports = {"$iterator", "$breaked"}
        else:
            self.refiner_ports = {"$iterator"}
        
    def subgraphs(self):
        return (self.body_graph, self.orelse_graph)
        
    def input_ports(self):
        body_inputs = {source.port for source, _ in  self.body_graph.get_out_connections(graph.START_TICK)}
        orelse_inputs = {source.port for source, _ in  self.orelse_graph.get_out_connections(graph.START_TICK)}
        
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}
        
        # we take care of `$target`, it isn't an input to the loop.
        body_inputs.remove("$target")

        if self.has_breaked_input:
            additional = {"$iterator", "$breaked"}
        else:
            additional = {"$iterator"}
            
        # in case of `break` neigher the body nor orelse is executed. In that case
        # this task will simply be removed. We need inputs for _all_ outputs so that we
        # can connect them to somewhere. Essentially there is a third option beside body and
        # orelse: an empty graph.
        
        return body_inputs | orelse_inputs | body_outputs | orelse_outputs | additional
        
    def output_ports(self):
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}
        
        return body_outputs | orelse_outputs
    
    def evaluate(self, inputs):
        raise ValueError("replaced by subgraph")
    
    def refine(self, g, tick, known_inputs):
        if "$iterator" not in known_inputs:
            return
        if self.has_breaked_input and "$breaked" not in known_inputs:
            return
        
        if self.has_breaked_input and known_inputs["$breaked"]:
            # `break` was called. Abort iteration
            refine.replace_task(g, tick, graph.Graph())
        
        iterator = known_inputs["$iterator"]
        
        try:
            item = next(iterator)
            use_body = True
        except StopIteration:
            use_body = False
            
        if use_body:
            if self.is_tail:
                # the last tick item is the for-tail
                # the prev. to last is the subgraph_tick
                # the one before that is the iteration_tick
                # and then we have the tick of the original for-loop task.
                orig_for_tick = tick >> 3
                #orig_for_tick = graph.Tick(tick._elements[:-3])
                iteration_counter = tick._elements[-3] + 1
                iteration_tick = graph.START_TICK + iteration_counter << orig_for_tick
            else:
                # First iteration
                iteration_counter = 1
                iteration_tick = graph.START_TICK + iteration_counter << tick
                
            item_tick = graph.START_TICK + 1 << iteration_tick
            subgraph_tick = graph.START_TICK + 2 << iteration_tick
            
            g.add_task(item_tick, ConstTask(item))
            item_endpoint = graph.Endpoint(item_tick, "value")
            
            refine.replace_task(g, tick, self.body_graph, 
                                subgraph_tick=subgraph_tick, 
                                additional_inputs={'$target':item_endpoint})
        else:
            refine.replace_task(g, tick, self.orelse_graph)
    
    def __repr__(self):
        return "ForTask(%s, %s, %s, %s)" % (self.is_tail, self.has_breaked_input, self.body_graph, self.orelse_graph)
    
    
class WhileTask(AbstractTask):
    
    def __init__(self, is_tail, has_breaked_input, body_graph, orelse_graph):
        """
        :param is_tail: If `False` this task represents the complete loop. If `True`
          it represents the reminder of the loop. The tail has `$breaed` as an
          additional input to know if the previous iteration aborted with `break`.
          There are also differences in the tick calculation when unrolling.
          
        :param has_breaked_input: If there is a `$breaked` input from a potential
          `break` statement during the previous iteration. 
        """
        self.is_tail = is_tail
        self.has_breaked_input = has_breaked_input
        self.body_graph = body_graph
        self.orelse_graph = orelse_graph
        
        if self.has_breaked_input:
            self.refiner_ports = {"$test", "$breaked"}
            self.refiner_reducer = {"$test": bool}
        else:
            self.refiner_ports = {"$test"}
            self.refiner_reducer = {"$test": bool, "$breaked": bool}
            
    def subgraphs(self):
        return (self.body_graph, self.orelse_graph)
        
    def input_ports(self):
        body_inputs = {source.port for source, _ in  self.body_graph.get_out_connections(graph.START_TICK)}
        orelse_inputs = {source.port for source, _ in  self.orelse_graph.get_out_connections(graph.START_TICK)}
        
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}

        if self.has_breaked_input:
            additional = {"$test", "$breaked"}
        else:
            additional = {"$test"}

            
        # in case of `break` neigher the body nor orelse is executed. In that case
        # this task will simply be removed. We need inputs for _all_ outputs so that we
        # can connect them to somewhere. Essentially there is a third option beside body and
        # orelse: an empty graph.
        
        return body_inputs | orelse_inputs | body_outputs | orelse_outputs | additional
        
    def output_ports(self):
        body_outputs = {dest.port for _, dest in  self.body_graph.get_in_connections(graph.FINAL_TICK)}
        orelse_outputs = {dest.port for _, dest in  self.orelse_graph.get_in_connections(graph.FINAL_TICK)}
        
        return body_outputs | orelse_outputs
    
    def evaluate(self, inputs):
        raise ValueError("replaced by subgraph")
    
    def refine(self, g, tick, known_inputs):
        if "$test" not in known_inputs:
            return
        if self.has_breaked_input and "$breaked" not in known_inputs:
            return
        
        if self.has_breaked_input and known_inputs["$breaked"]:
            # `break` was called. Abort iteration
            refine.replace_task(g, tick, graph.Graph())
        
        test = known_inputs["$test"]
        
        use_body = test == True
            
        if use_body:
            if self.is_tail:
                # the last tick item is the tail
                # the one before that is the iteration_tick
                # and then we have the tick of the original loop task.
                orig_for_tick = tick >> 2
                iteration_counter = tick._elements[-2] + 1
                iteration_tick = graph.START_TICK + iteration_counter << orig_for_tick
            else:
                # First iteration
                iteration_counter = 1
                iteration_tick = graph.START_TICK + iteration_counter << tick
                
            subgraph_tick = iteration_tick
            
            refine.replace_task(g, tick, self.body_graph, 
                                subgraph_tick=subgraph_tick)
        else:
            refine.replace_task(g, tick, self.orelse_graph)
    
    def __repr__(self):
        return "WhileTask(%s, %s, %s, %s)" % (self.is_tail, self.has_breaked_input, self.body_graph, self.orelse_graph)
    
    
    
class AttrAssign(AbstractTask):
    
    def __init__(self, attribute):
        self.attribute = attribute
    
    def input_ports(self):
        return {"object", "value"}
    
    def output_ports(self):
        return set()
    

    def evaluate(self, inputs):
        setattr(inputs["object"], self.attribute, inputs["value"])
        return {}
        
    def __repr__(self):
        return "AttrAssign(%s)" % self.attribute
    

class SubscriptAssign(AbstractTask):
    
    def input_ports(self):
        return {"object", "slice", "value"}
    
    def output_ports(self):
        return set()
    

    def evaluate(self, inputs):
        obj = inputs["object"]
        sl = inputs["slice"]
        value = inputs["value"]
        obj[sl] = value
        return {}
        
    def __repr__(self):
        return "SubscriptAssign()"
    
class UnpackTask(AbstractTask):
    
    def __init__(self, elt_count):
        self.elt_count = elt_count
        
    def input_ports(self):
        return {"value"}
        
    def output_ports(self):
        return {str(i) for i in range(self.elt_count)}
    
    def evaluate(self, inputs):
        value = inputs["value"]
        it = iter(value)
        return {str(i): next(it) for i in range(self.elt_count)}

    def __repr__(self):
        return "UnpackTask(%s)" % repr(self.elt_count)


class AugAssignTask(AbstractTask):
    
    def __init__(self, operator):
        self.operator = operator.__class__
        
    def input_ports(self):
        return {"target", "value"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        target = inputs["target"]
        value = inputs["value"]
        target = utils.augassign(target, value, self.operator)
        return {"value":target}
    
    def __repr__(self):
        return "AugAssignTask(%s)" % repr(self.operator)

    
class AugAttrAssignTask(AbstractTask):
    
    def __init__(self, operator, attribute):
        self.attribute = attribute
        self.operator = operator.__class__
        
    def input_ports(self):
        return {"target", "value"}
    
    def output_ports(self):
        return set()
    
    def evaluate(self, inputs):
        target = inputs["target"]
        value = inputs["value"]
        
        v = getattr(target, self.attribute)
        v = utils.augassign(v, value, self.operator)
        setattr(target, self.attribute, v)
            
        return {}

    def __repr__(self):
        return "AugAttrAssignTask(%s, %s)" % (repr(self.operator), repr(self.attribute))

class AugSubscriptAssignTask(AbstractTask):
    
    def __init__(self, operator):
        self.operator = operator.__class__
        
    def input_ports(self):
        return {"target", "slice", "value"}
    
    def output_ports(self):
        return set()
    
    def evaluate(self, inputs):
        target = inputs["target"]
        sl = input["slice"]
        value = inputs["value"]
        
        v = target[sl]
        v = utils.augassign(v, value, self.operator)
        target[sl] = v
            
        return {}

    def __repr__(self):
        return "AugSubscriptAssignTask(%s)" % repr(self.operator)
    
    

class RaiseTask(AbstractTask):

    def input_ports(self):
        return {"type", "inst", "tback"}
    
    def output_ports(self):
        return set()
    
    def evaluate(self, inputs):
        t = inputs["type"]
        i = input["inst"]
        tb = inputs["tback"]
        
        raise t, i, tb

    def __repr__(self):
        return "RaiseTask()"
    

class BinOpTask(AbstractTask):
    
    def __init__(self, op):
        self.operator = op.__class__

    def input_ports(self):
        return {"left", "right"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        left = inputs["left"]
        right = inputs["right"]
        value = utils.binop(left, right, self.operator)
        return {"value":value}
    
    def __repr__(self):
        return "BinOpTask(%s)" % self.operator
    
class UnaryOpTask(AbstractTask):
    
    def __init__(self, op):
        self.operator = op.__class__

    def input_ports(self):
        return {"value"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        value = inputs["value"]
        return {"value": utils.unaryop(value, self.operator)}

    def __repr__(self):
        return "UnaryOpTask(%s)" % self.operator
    
class DictTask(AbstractTask):
    
    def __init__(self, num_items):
        self.num_items = num_items

    def input_ports(self):
        return {"key_%s" % i for i in range(self.num_items)} |  {"value_%s" % i for i in range(self.num_items)}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {"value": {inputs["key_%s" % i]: inputs["value_%s" % i] for i in range(self.num_items)}}
            
    def __repr__(self):
        return "Dict(%s)" % self.num_items
    
    
class SetTask(AbstractTask):
    
    def __init__(self, num_items):
        self.num_items = num_items

    def input_ports(self):
        return {"value_%s" % i for i in range(self.num_items)}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {"value": {inputs["value_%s" % i] for i in range(self.num_items)}}
            
    def __repr__(self):
        return "Set(%s)" % self.num_items
    
class ListTask(AbstractTask):
    
    def __init__(self, num_items):
        self.num_items = num_items

    def input_ports(self):
        return {"value_%s" % i for i in range(self.num_items)}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {"value": [inputs["value_%s" % i] for i in range(self.num_items)]}
            
    def __repr__(self):
        return "ListTask(%s)" % self.num_items
    
class TupleTask(AbstractTask):
    
    def __init__(self, num_items):
        self.num_items = num_items

    def input_ports(self):
        return {"value_%s" % i for i in range(self.num_items)}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {"value":tuple([inputs["value_%s" % i] for i in range(self.num_items)])}
            
    def __repr__(self):
        return "TupleTask(%s)" % self.num_items
    
    
def _is_functional(func):
    functional = getattr(func, "functional", func in whitelist.functional_whitelist)
    return functional
    
class CallTask(AbstractTask):

    refiner_ports = {"func"}
    refiner_reducer = {"func": _is_functional}
    
    def __init__(self, numargs, keywords, has_starargs, has_kwargs):
        self.numargs = numargs
        self.keywords = keywords
        self.has_starargs = has_starargs
        self.has_kwargs = has_kwargs
        
    def input_ports(self):
        args = {"arg_%s" % i for i in range(self.numargs)}
        kargs = {"karg_%s" % i for i in range(len(self.keywords))}
        starargs = {"starargs"} if self.has_starargs else set()
        kwargs = {"kwargs"} if self.has_kwargs else set()
        
        return {"func"} | args | kargs | starargs | kwargs
    
    def output_ports(self):
        return {"value"}    
    
    def evaluate(self, inputs):
        func = inputs["func"]
        args = tuple(inputs["arg_%s" % i] for i in range(self.numargs))
        kargs = tuple([inputs["karg_%s" % i] for i in range(len(self.keywords))])
        starargs = inputs["starargs"] if self.has_starargs else tuple()
        kwargs = inputs["kwargs"] if self.has_kwargs else {}
        
        for k, v in zip(self.keywords, kargs):
            if k in kwargs:
                raise TypeError("Specified keyword %s twice." % repr(k))
            kwargs[k] = v
        
        args = args + starargs
        
        retval = func(*args, **kwargs)
        
        return {"value":retval}
    
    def refine(self, g, tick, known_inputs):
        functional = known_inputs["func"]
        
        if functional:
            g.set_task_property(tick, "syncpoint", False)

                
    def __repr__(self):
        return "Call(%s, %s, %s, %s)" % (self.numargs, repr(self.keywords), self.has_starargs, self.has_kwargs)
    

    
class ReprTask(AbstractTask):

    def input_ports(self):
        return {"value"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        return {"value":repr(inputs["value"])}
            
    def __repr__(self):
        return "ReprTask()"
    
class AttributeTask(AbstractTask):
    
    def __init__(self, attribute):
        self.attribute = attribute

    def input_ports(self):
        return {"object"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        obj = inputs["object"]
        value = getattr(obj, self.attribute)
        return {"value":value}
            
    def __repr__(self):
        return "AttributeTask(%s)" % self.attribute
    
class SubscriptTask(AbstractTask):

    def input_ports(self):
        return {"object", "slice"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        obj = inputs["object"]
        sl = inputs["slice"]
        value= obj[sl]
        return {"value":value}
            
    def __repr__(self):
        return "SubscriptTask()"
    
class BuiltinCallTask(AbstractTask):
    
    def __init__(self, builtin_function, num_args):
        self.builtin_function = builtin_function
        self.num_args = num_args

    def input_ports(self):
        return {"arg%s" % i for i in range(self.num_args)}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        args = tuple(inputs["arg%s" % i]  for i in range(self.num_args))
        return {"value":self.builtin_function(*args)}
            
    def __repr__(self):
        return "BuiltinCallTask(%s, %s)" % (self.num_args, self.builtin_function)
    
class ReadGlobal(AbstractTask):
    
    def __init__(self, module_name):
        self.module_name = module_name
        
    def input_ports(self):
        return {"var"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        var = inputs["var"]
        
        # In `tranlator.translate_function` we try to use the
        # full module name even for __main__ because we need it
        # on other workers. But if we happen to run on the
        # node where the module really is __main__ then we don't want
        # to make a mess, so we use __main__ again.
        main_mod = sys.modules["__main__"]
        module = importlib.import_module(self.module_name)
        if hasattr(module, "__file__") and hasattr(main_mod, "__file__"):
            if module.__file__ == main_mod.__file__:
                module = main_mod
            
        
        try:
            value = getattr(module, var)
        except AttributeError:
            try:
                value = getattr(__builtin__, var)
            except AttributeError:
                raise NameError("global name %r is not defined in %r." % (var, module))
        return {"value":value}
            
    def __repr__(self):
        return "ReadGlobal(%r)" % (self.module_name)
    
class AssignGlobal(AbstractTask):
    
    def __init__(self, module_name):
        self.module_name = module_name
        
    def input_ports(self):
        return {"var", "value"}
    
    def output_ports(self):
        return {"value"}
    
    def evaluate(self, inputs):
        var = inputs["var"]
        value = inputs["value"]
        module = importlib.import_module(self.module_name)
        setattr(module, var, value)
        return {"value": None}
            
    def __repr__(self):
        return "AssignGlobal(%r)" % (self.module_name)
    
    
class NextTask(AbstractTask):
    """
    Task for __pydron_next__. We cannot use CallTask since it returns
    the iterator which needs the nosend flag as well as the value
    which doesn't.
    """
    
    def input_ports(self):
        return {"iterator"}
    
    def output_ports(self):
        return {"iterator", "value"}
    
    def evaluate(self, inputs):
        iterator = inputs["iterator"]
        value, iterator = builtins.__pydron_next__(iterator)
        return {"value":value, "iterator":iterator}
    
    def __repr__(self):
        return "NextTask()"
    