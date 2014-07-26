
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

peer_name = "sec_server"

logging.basicConfig(filename='%s.log' % peer_name, level=logging.DEBUG)


class ServerControlEndpoint(object):
    target = messaging.Target(namespace='control',
                              version='2.0')

    def __init__(self, server=None):
        self.server = server

    def stop(self, ctx):
        self.server.stop()


class TestEndpoint(object):
    target = messaging.Target(version='2.0')

    def test(self, ctx, arg):
        print("Got call: ", arg)
        return "echo '%s'" % arg

# setup config opts
cfg.set_defaults(messaging.transport._transport_opts,
                 sec_policy_name="kite")

group = cfg.OptGroup(name='kite_plugin', title="Kite Secure RPC Plugin.")
ident = cfg.StrOpt('identity', default=peer_name)
cfg.CONF.register_group(group)
cfg.CONF.register_opt(ident, group=group)

transport = messaging.get_transport(cfg.CONF, "rabbit://localhost")

# NOTE(tkelsey): when listening, the peer name should match the topic
# name we are interested in. This is needed since it will be the key
# name we use when the transmitting client requests a ticket from kite.
#
target = messaging.Target(topic=peer_name,
                          server='server1',
                          version='2.0')

endpoints = [
    ServerControlEndpoint(),
    TestEndpoint(),
]

server = messaging.get_rpc_server(transport, target, endpoints)
endpoints[0].server = server
try:
    server.start()
    server.wait()

except KeyboardInterrupt:
    print()
