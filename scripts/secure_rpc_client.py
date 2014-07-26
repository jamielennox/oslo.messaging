
# Copyright 2014 HP, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function

import logging

from oslo.config import cfg
from oslo import messaging

peer_name = "sec_client"
serv_name = "sec_server"

logging.basicConfig(filename='%s.log' % peer_name, level=logging.DEBUG)


class TestClient(object):

    def __init__(self, transport):
        target = messaging.Target(topic=serv_name, version='2.0')
        self._client = messaging.RPCClient(transport, target)

    def testCall(self, arg):
        return self._client.call({}, 'test', arg=arg)

    def testCast(self, arg):
        return self._client.cast({}, 'test', arg=arg)

cfg.set_defaults(messaging.transport._transport_opts,
                 sec_policy_name="kite")

group = cfg.OptGroup(name='kite_plugin', title="Kite Secure RPC Plugin.")
ident = cfg.StrOpt('identity', default=peer_name)
cfg.CONF.register_group(group)
cfg.CONF.register_opt(ident, group=group)

transport = messaging.get_transport(cfg.CONF, "rabbit://localhost")

c = TestClient(transport)
print("Call:")
resp = c.testCall("test")
print("GOT: ", resp)

print("Cast:")
resp = c.testCast("test")
