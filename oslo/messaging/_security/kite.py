
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

from oslo.config import cfg
from oslo.messaging import security

from keystoneclient.auth import token_endpoint
from keystoneclient import session
from kiteclient import v1

import logging

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

_kite_plugin_group = cfg.OptGroup(name='kite_plugin',
                                  title="Kite Secure RPC Plugin.")

_kite_plugin_opts = [
    cfg.StrOpt('sec_identity',
               help='An identity for this peer, It will be used to '
                    'identify the peer to Kite, i.e. the key name that '
                    'will be used. If running as a server then this '
                    'should match the topic name.'),

    cfg.StrOpt('host', default="localhost",
               help="The kite host address"),

    cfg.IntOpt('port', default=9109,
               help="The kite port number.")
]

CONF.register_group(_kite_plugin_group)
CONF.register_opts(_kite_plugin_opts, group=_kite_plugin_group)


def getSession(conf):
    # NOTE(tkelsey): using developer interface to remove the need to run
    # a keystone server.
    host = conf.kite_plugin.host
    port = conf.kite_plugin.port
    kite = "http://%s:%s/v1" % (host, port)
    auth = token_endpoint.Token(kite, 'aToken')
    return session.Session(auth=auth)


class KiteSecPolicy(security.SecurityPolicyBase):
    """This security policy provides message level security through the
    use of Kite. A Kite server and a Keystone server must be available.
    """

    def __init__(self, conf, key=None):
        super(KiteSecPolicy, self).__init__(conf)
        self.identity = conf.kite_plugin.identity
        if not self.identity:
            raise RuntimeError(("sec_identity must be set if using the "
                                "Kite security policy"))

        LOG.debug("Peer identified as %s" % self.identity)
        self._session = getSession(conf)

        try:
            if key is None:
                self._key = v1.Key.generate(self.identity, self._session)
            else:
                self._key = v1.Key(self.identity, key, self._session)
        except Exception as e:
            LOG.error(e)
            raise

    def _get_ticket(self, target):
        # TODO(tim.kelsey) use a cache here ....
        ticket = v1.Ticket(self._key, target, session=self._session)
        return ticket

    def encrypt(self, target, message):
        """Secure a message to a given target."""
        LOG.debug("Securing Message: %s", message)
        ticket = self._get_ticket(target)
        enc, sig = ticket.encrypt(str(message))
        data = {
            "sender": self._key.key_name,
            "body": enc,
            "signature": sig,
            "esek": ticket.b64_esek
        }

        LOG.debug("Secured Message: %s", data)
        return data

    def decrypt(self, message):
        """Decrypt and verify a secure message.
        This method will throw an exception if the message fails
        can not be decrypted successfully (fails a signature check)

        :param message: The message data to decrypt. It should have the
                        form { "sender": ...,
                               "body": ...,
                               "esek": ...
                         }
        :type message: dict
        :return: the decrypted message body, as a string.
        """
        LOG.debug("Got secure message: %s", message)

        try:
            esek = v1.Esek(message["sender"], self._key, message["esek"])
            body = esek.decrypt(message["body"], message["signature"],
                                b64decode=True)
        except Exception as e:
            raise security.SecurityValidityFailure(e)

        LOG.debug("Decrypted message: %s", body)
        return body
