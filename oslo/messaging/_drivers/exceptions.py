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
import sys

from oslo.messaging import exceptions
import six

# FIXME(markmc): remove this
_ = lambda s: s

LOG = logging.getLogger(__name__)


class ClientException(Exception):
    """Encapsulates actual exception expected to be hit by a RPC proxy object.

    Merely instantiating it records the current exception information, which
    will be passed back to the RPC client without exceptional logging.
    """
    def __init__(self):
        self._exc_info = sys.exc_info()


class TransportDriverError(exceptions.MessagingException):
    """Base class for transport driver specific exceptions."""


class RPCException(Exception):
    msg_fmt = _("An unknown RPC related exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_('Exception in string format operation'))
                for name, value in six.iteritems(kwargs):
                    LOG.error("%s: %s" % (name, value))
                # at least get the core message out if something happened
                message = self.msg_fmt

        super(RPCException, self).__init__(message)


class Timeout(RPCException):
    """Signifies that a timeout has occurred.

    This exception is raised if the rpc_response_timeout is reached while
    waiting for a response from the remote side.
    """
    msg_fmt = _('Timeout while waiting on RPC response - '
                'topic: "%(topic)s", RPC method: "%(method)s" '
                'info: "%(info)s"')

    def __init__(self, info=None, topic=None, method=None):
        """Initiates Timeout object.

        :param info: Extra info to convey to the user
        :param topic: The topic that the rpc call was sent to
        :param rpc_method_name: The name of the rpc method being
                                called
        """
        self.info = info
        self.topic = topic
        self.method = method
        super(Timeout, self).__init__(
            None,
            info=info or _('<unknown>'),
            topic=topic or _('<unknown>'),
            method=method or _('<unknown>'))


class DuplicateMessageError(RPCException):
    msg_fmt = _("Found duplicate message(%(msg_id)s). Skipping it.")


class InvalidRPCConnectionReuse(RPCException):
    msg_fmt = _("Invalid reuse of an RPC connection.")


class UnsupportedRpcVersion(RPCException):
    msg_fmt = _("Specified RPC version, %(version)s, not supported by "
                "this endpoint.")


class UnsupportedRpcEnvelopeVersion(RPCException):
    msg_fmt = _("Specified RPC envelope version, %(version)s, "
                "not supported by this endpoint.")


class RpcVersionCapError(RPCException):
    msg_fmt = _("Specified RPC version cap, %(version_cap)s, is too low")
