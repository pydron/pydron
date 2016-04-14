# Copyright (C) 2015 Stefan C. Mueller

import unittest
from pydron.config import config
import anycall
from twisted.internet import defer, reactor, task

import utwist
import json

class TestConfig(unittest.TestCase):
    
    @defer.inlineCallbacks
    def twisted_setup(self):
        self.rpc = anycall.create_tcp_rpc_system()
        anycall.RPCSystem.default = self.rpc
        
        yield self.rpc.open()
        
    @defer.inlineCallbacks
    def twisted_teardown(self):
        yield self.rpc.close()
        
    
    @utwist.with_reactor
    @defer.inlineCallbacks
    def test_multicore(self):
        
        conf="""{
        "workers": [
            {
            "type":"multicore", 
            "cores":1
            }
        ]
        }"""
        conf = json.loads(conf)
        
        pool = yield config.create_pool(conf, self.rpc, None)
        
        self.assertEquals(1, len(pool.get_workers()))
        
        yield pool.stop()
        
        
    @utwist.with_reactor
    @defer.inlineCallbacks
    def test_multicore_2(self):
        
        conf="""{
        "workers": [
            {
            "type":"multicore", 
            "cores":2
            }
        ]
        }"""
        conf = json.loads(conf)
        
        pool = yield config.create_pool(conf, self.rpc, None)
        self.assertEquals(2, len(pool.get_workers()))
        
        yield pool.stop()
        