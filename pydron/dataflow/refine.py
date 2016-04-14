# Copyright (C) 2015 Stefan C. Mueller

"""
Methods that help with changeing the graph.
"""

from pydron.dataflow import graph
    
def replace_task(g, tick, subgraph, subgraph_tick=None, additional_inputs={}):
    """
    Replaces the task in `g` at `tick` with `subgraph`.
    
    All tasks of the subgraph will be shifted by `subgraph_tick`. If `subgraph_tick` is `None`
    then the tasks are shifted by `tick`.
    
    All inputs of the subgraph are connected to source endpoints in `g`. Endpoints for input port
    `p` are searched as follows:
    
    * if `p` is a key in  `additional_inputs` then the value is expected to be the endpoint in `g`
      to use.
      
    * if the replaced task has an input port named `p`, then the endpoint which connects to that port
      is used.
      
    * if none of the above matches, fail with an exception.
    
    For each output port `p` of the replaced task, the destination endpoint in `g` will be connected 
    to another source endpoint
    
    * if the subgraph has an output `g` then it is connected to the source of that output.
      If the source of that output is an input to the subgraph, then the source is searched using
      the rules above for inputs of the subgraph.
      
    * use the rules for inputs to find the source. This will fail if there is none to be found.

    """
    
    if subgraph_tick is None:
        subgraph_tick = tick
    
    task_input_map = {dest.port: source for source, dest in g.get_in_connections(tick)}
    task_input_map.update(additional_inputs)
    
    subgraph_output_map = {dest.port: source for source, dest in subgraph.get_in_connections(graph.FINAL_TICK)}
    

    # Prepare the connections to hook up the subgraph's inputs.
    input_connections = []
    for source, dest in subgraph.get_out_connections(graph.START_TICK):
        task_input = task_input_map[source.port]
        if dest.tick == graph.FINAL_TICK:
            continue # direct connection are treated as output connecions.
        else:
            subgraph_dest = graph.Endpoint(dest.tick << subgraph_tick, dest.port)
            input_connections.append((task_input, subgraph_dest))
        
    # Prepare the connections to replace the ones of the removed task.
    output_connections = []
    for source, dest in g.get_out_connections(tick):
        if source.port in subgraph_output_map:
            # output is assigned in the subgraph
            source = subgraph_output_map[source.port]
            if source.tick == graph.START_TICK:
                # not connected to a task in the subgraph. This is a connection from
                # START_TICK to FINAL_TICK. We have to find the task input for this.
                source = task_input_map[source.port]
            else:
                source = graph.Endpoint(source.tick << subgraph_tick, source.port)
        elif source.port in task_input_map:
            # output is not assigned, but is an input to the replaced task.
            # Just pass it through.
            source = task_input_map[source.port]
        else:
            raise ValueError("No input on the replaced task for output %s" % `source.port`)
        output_connections.append((source, dest))
    
    # Remove the task
    for source, dest in g.get_in_connections(tick):
        g.disconnect(source, dest)
    for source, dest in g.get_out_connections(tick):
        g.disconnect(source, dest)
    g.remove_task(tick)
    
    # Insert subgraph, make connections
    insert_subgraph(g, subgraph, subgraph_tick)
    for source, dest in input_connections:
        g.connect(source, dest)
    for source, dest in output_connections:
        g.connect(source, dest)
    

def insert_subgraph(g, subgraph, supertick):
    """
    Inserts all tasks and connections between them from `subgraph` into `g`.
    All ticks are shifted by `supertick`. The connections to START_TICK and FINAL_TICK
    are NOT copied.
    """
    
    for tick in subgraph.get_all_ticks():
        newtick = tick << supertick
        g.add_task(newtick, subgraph.get_task(tick), subgraph.get_task_properties(tick))
        
    
    for tick in list(subgraph.get_all_ticks()) + [graph.FINAL_TICK]:
        
        for source, dest in subgraph.get_in_connections(tick):
            if source.tick == graph.START_TICK or dest.tick == graph.FINAL_TICK:
                continue
            g.connect(graph.Endpoint(source.tick << supertick, source.port),
                      graph.Endpoint(dest.tick << supertick, dest.port))
        
        