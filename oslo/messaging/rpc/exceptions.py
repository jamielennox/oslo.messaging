# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

LOG = logging.getLogger(__name__)

from oslo.messaging import exceptions


# FIXME(markmc): remove this
_ = lambda s: s


__all__ = ['ClientSendError',
           'RPCVersionCapError',
           'RemoteError']


class RemoteError(exceptions.MessagingException):

    """Signifies that a remote endpoint method has raised an exception.

    Contains a string representation of the type of the original exception,
    the value of the original exception, and the traceback.  These are
    sent to the parent as a joined string so printing the exception
    contains all of the relevant info.
    """

    def __init__(self, exc_type=None, value=None, traceback=None):
        self.exc_type = exc_type
        self.value = value
        self.traceback = traceback
        msg = ("Remote error: %(exc_type)s %(value)s\n%(traceback)s." %
               dict(exc_type=self.exc_type, value=self.value,
                    traceback=self.traceback))
        super(RemoteError, self).__init__(msg)


class RPCVersionCapError(exceptions.MessagingException):

    def __init__(self, version, version_cap):
        self.version = version
        self.version_cap = version_cap
        msg = ("Specified RPC version cap, %(version_cap)s, is too low. "
               "Needs to be higher than %(version)s." %
               dict(version=self.version, version_cap=self.version_cap))
        super(RPCVersionCapError, self).__init__(msg)


class ClientSendError(exceptions.MessagingException):
    """Raised if we failed to send a message to a target."""

    def __init__(self, target, ex):
        msg = 'Failed to send to target "%s": %s' % (target, ex)
        super(ClientSendError, self).__init__(msg)
        self.target = target
        self.ex = ex
