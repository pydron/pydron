# Copyright (C) 2015 Stefan C. Mueller

import json
import os.path
from remoot import pythonstarter, smartstarter
import anycall
from pydron.backend import worker
from pydron.interpreter import scheduler, strategies
from twisted.internet import defer

preload_packages = []

def load_config(configfile=None):
    
    if not configfile:
        candidates = []
        if "PYDRON_CONF" in os.environ:
            candidates.append(os.environ["PYDRON_CONF"])
        candidates.append(os.path.abspath("pydron.conf"))
        candidates.append(os.path.expanduser("~/pydron.conf"))
        candidates.append("/etc/pydron.conf")
        for candidate in candidates:
            if os.path.exists(candidate):
                configfile = candidate
                break
        else:
            raise ValueError("Config file could not be found. Looked for %s" % repr(candidates))
        
    with open(configfile, 'r') as f:
        cfg = json.load(f)
        
    def convert(obj):
        if isinstance(obj, dict):
            return {k:convert(v) for k,v in obj.iteritems()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        elif isinstance(obj, unicode):
            return str(obj)
        else:
            return obj
        
    cfg = convert(cfg)
    return cfg

def create_scheduler(config, pool):
    if "scheduler" not in config:
        strategy_name = "trivial"
    else:
        strategy_name = config["scheduler"]
    
    if strategy_name == "trivial":
        strategy = strategies.TrivialSchedulingStrategy(pool)
        strategy = strategies.VerifySchedulingStrategy(strategy)
    else:
        raise ValueError("Unsupported scheduler: %s" % strategy_name)
    
    return scheduler.Scheduler(pool, strategy)
    

def create_pool(config, rpcsystem, error_handler):
    """
    starts workers and returns a pool of them.
    
    Returns two callbacks:
    
    * The first callbacks with the pool as 
    soon as there is one worker. Errbacks if all starters
    failed to create a worker.
    
    * The second calls back once all workers have been
    started. This one can be cancelled.
    
    The given `error_handler` is invoked for every failed start.
    """
    
    starters = []
    
    for starter_conf in config["workers"]:
        starters.extend(_create_starters(starter_conf, rpcsystem))
        
    pool = worker.Pool()
    
    ds = []
    
    for i, starter in enumerate(starters):
        d = starter.start()
        
        def success(worker, i, starter):
            worker.nicename = "#%s" % i
            pool.add_worker(worker)
        def fail(failure):
            error_handler(failure)
            return failure

        d.addCallback(success, i, starter)
        ds.append(d)
        
    d = defer.DeferredList(ds, fireOnOneErrback=True, consumeErrors=True)
    
    def on_success(result):
        return pool
    def on_fail(firsterror):
        return firsterror.value.subFailure
    d.addCallbacks(on_success, on_fail)
    return d


def create_rpc_system(conf):
    port_range = _parse_port_range(conf.get("data_ports", 0))
    
    return anycall.create_tcp_rpc_system(port_range = port_range)


def _create_starters(conf, rpcsystem):
    global preload_packages
    import pydron
    
    data_ports = _parse_port_range(conf.get("data_ports", 0))
    preconnect = conf.get("preconnect", True)
    
    if 0 in data_ports:
        # use automatically selected ports. this is not compatible
        # with preconnect
        preconnect = False
        data_ports = [0]

    if data_ports != [0] and len(data_ports) <= conf["cores"]:
        if 0  not in data_ports:
            raise ValueError("Not enough ports configured for %r" % conf)
    
    starters = []
    for i in range(conf["cores"]):
        starter_type = conf["type"]
        
        if starter_type == "multicore":
            starter = _multicore_starter(conf, rpcsystem)
        elif starter_type == "ssh":
            starter = _ssh_starter(conf, rpcsystem)
        elif starter_type == "cloud":
            starter = _ec2_starter(conf, rpcsystem)
        else:
            raise ValueError("Not supported worker type %s" % repr(starter_type))
        
        if data_ports == [0]:
            port = 0
        else:
            port = data_ports[i]
        
        smart = smartstarter.SmartStarter(starter, 
                                          rpcsystem, 
                                          anycall.create_tcp_rpc_system, 
                                          list(preload_packages)+[pydron],
                                          preconnect = preconnect,
                                          data_port = port)
        
        starters.append(worker.WorkerStarter(smart))
    
    return starters
        
def _multicore_starter(conf, rpcsystem):
    return pythonstarter.LocalStarter()
    

def _ssh_starter(conf, rpcsystem):
    starter = pythonstarter.SSHStarter(conf["hostname"], 
                                       username=conf["username"], 
                                       password=conf.get("password", None), 
                                       private_key_files=conf.get("private_key_files", []),
                                       private_keys=conf.get("private_keys", []), 
                                       tmp_dir=conf.get("tmp_dir", "/tmp"))
    return starter

def _ec2_starter(conf, rpcsystem):
    starter = pythonstarter.EC2Starter(username=conf["username"], 
                                       provider=conf["provider"], 
                                       provider_keyid=conf["accesskeyid"], 
                                       provider_key=conf["accesskey"], 
                                       image_id=conf["imageid"],
                                       size_id=conf["sizeid"], 
                                       public_key_file=conf["publickey"],
                                       private_key_file=conf["privatekey"],
                                       tmp_dir=conf.get("tmp_dir", "/tmp"))
    return starter

def _parse_port_range(ports):
    try:
        return [int(ports)]
    except ValueError:
        pass
    
    if isinstance(ports, list):
        return [int(x) for x in ports]
        
    min_port, max_port = str(ports).split('-', 1)
    min_port = int(min_port)
    max_port = int(max_port)
    return range(min_port, max_port + 1)

