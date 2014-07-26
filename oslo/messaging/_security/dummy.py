
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

from oslo.messaging import security

import logging

LOG = logging.getLogger(__name__)


class DummySecPolicy(security.SecurityPolicyBase):
    """This is a dummy pass-through security policy."""

    def __init__(self, conf):
        super(DummySecPolicy, self).__init__(conf)

    def encrypt(self, target, message):
        """Secure a message to a given target."""
        LOG.debug("Securing Message: %s", message)
        return {"message": str(message),
                "sender": None}  # maybe this should know about the sender

    def decrypt(self, message):
        LOG.debug("Decrypting message: %s", message)
        return message["message"]
