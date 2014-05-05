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

import abc
import logging
import traceback

from oslo.config import cfg
import six

from oslo.messaging import _utils as utils
from oslo.messaging.openstack.common import importutils
from oslo.messaging.openstack.common import jsonutils
from oslo.messaging.rpc import exceptions as rpc_exceptions

__all__ = ['RPCProtocol',
           'OpenStackRPC2']

LOG = logging.getLogger(__name__)

_EXCEPTIONS_MODULE = 'exceptions' if six.PY2 else 'builtins'

_exception_opts = [
    cfg.ListOpt('allowed_rpc_exception_modules',
                default=['oslo.messaging.exceptions',
                         'nova.exception',
                         'cinder.exception',
                         _EXCEPTIONS_MODULE,
                         ],
                help='Modules of exceptions that are permitted to be '
                     'recreated upon receiving exception data from an rpc '
                     'call.'),
]

# FIXME(markmc): remove this
_ = lambda s: s


@six.add_metaclass(abc.ABCMeta)
class RPCProtocol(object):

    def __init__(self, conf):
        self.conf = conf

    @abc.abstractmethod
    def serialize_msg(self, raw_msg):
        return None

    @abc.abstractmethod
    def deserialize_msg(self, msg):
        return None

    @abc.abstractmethod
    def serialize_exception(self, failure_info, log_failure=True):
        """Prepares exception data to be sent over rpc.

        Failure_info should be a sys.exc_info() tuple.

        """

        return failure_info

    @abc.abstractmethod
    def deserialize_exception(self, e):
        return None


'''RPC Envelope Version.

This version number applies to the top level structure of messages sent out.
It does *not* apply to the message payload, which must be versioned
independently.  For example, when using rpc APIs, a version number is applied
for changes to the API being exposed over rpc.  This version number is handled
in the rpc proxy and dispatcher modules.

This version number applies to the message envelope that is used in the
serialization done inside the rpc layer.  See serialize_msg() and
deserialize_msg().

The current message format (version 2.0) is very simple.  It is:

    {
        'oslo.version': <RPC Envelope Version as a String>,
        'oslo.message': <Application Message Payload, JSON encoded>
    }

Message format version '1.0' is just considered to be the messages we sent
without a message envelope.

So, the current message envelope just includes the envelope version.  It may
eventually contain additional information, such as a signature for the message
payload.

We will JSON encode the application message payload.  The message envelope,
which includes the JSON encoded application message body, will be passed down
to the messaging libraries as a dict.
'''


class OpenStackRPC2(RPCProtocol):

    _RPC_ENVELOPE_VERSION = '2.0'

    _VERSION_KEY = 'oslo.version'
    _MESSAGE_KEY = 'oslo.message'

    _REMOTE_POSTFIX = '_Remote'

    def serialize_msg(self, target, raw_msg):
        # NOTE(russellb) See the docstring for _RPC_ENVELOPE_VERSION for more
        # information about this format.
        msg = {self._VERSION_KEY: self._RPC_ENVELOPE_VERSION,
               self._MESSAGE_KEY: jsonutils.dumps(raw_msg)}

        return msg

    def deserialize_msg(self, msg):
        # NOTE(russellb): Hang on to your hats, this road is about to
        # get a little bumpy.
        #
        # Robustness Principle:
        #    "Be strict in what you send, liberal in what you accept."
        #
        # At this point we have to do a bit of guessing about what it
        # is we just received.  Here is the set of possibilities:
        #
        # 1) We received a dict.  This could be 2 things:
        #
        #   a) Inspect it to see if it looks like a standard message envelope.
        #      If so, great!
        #
        #   b) If it doesn't look like a standard message envelope, it could
        #      either be a notification, or a message from before we added a
        #      message envelope (referred to as version 1.0).  Just return the
        #      message as-is.
        #
        # 2) It's any other non-dict type.  Just return it and hope for the
        #    best.  This case covers return values from rpc.call() from before
        #    message envelopes were used.  (messages to call a method were
        #    always a dict)

        if not isinstance(msg, dict):
            # See #2 above.
            return msg

        base_envelope_keys = (self._VERSION_KEY, self._MESSAGE_KEY)
        if not all(map(lambda key: key in msg, base_envelope_keys)):
            #  See #1.b above.
            return msg

        # At this point we think we have the message envelope
        # format we were expecting. (#1.a above)

        if not utils.version_is_compatible(self._RPC_ENVELOPE_VERSION,
                                           msg[self._VERSION_KEY]):
            version = msg[self._VERSION_KEY]
            raise rpc_exceptions.UnsupportedRpcEnvelopeVersion(version=version)

        raw_msg = jsonutils.loads(msg[self._MESSAGE_KEY])

        return raw_msg

    def serialize_exception(self, failure_info, log_failure=True):
        """Prepares exception data to be sent over rpc.

        Failure_info should be a sys.exc_info() tuple.

        """
        tb = traceback.format_exception(*failure_info)
        failure = failure_info[1]

        if log_failure:
            LOG.error(_("Returning exception %s to caller"),
                      six.text_type(failure))
            LOG.error(tb)

        kwargs = {}
        if hasattr(failure, 'kwargs'):
            kwargs = failure.kwargs

        # NOTE(matiu): With cells, it's possible to re-raise remote, remote
        # exceptions. Lets turn it back into the original exception type.
        cls_name = str(failure.__class__.__name__)
        mod_name = str(failure.__class__.__module__)
        if (cls_name.endswith(self._REMOTE_POSTFIX) and
                mod_name.endswith(self._REMOTE_POSTFIX)):
            cls_name = cls_name[:-len(self._REMOTE_POSTFIX)]
            mod_name = mod_name[:-len(self._REMOTE_POSTFIX)]

        data = {
            'class': cls_name,
            'module': mod_name,
            'message': six.text_type(failure),
            'tb': tb,
            'args': failure.args,
            'kwargs': kwargs
        }

        return jsonutils.dumps(data)

    def deserialize_exception(self, data, allowed_remote_exmods):
        failure = jsonutils.loads(str(data))

        trace = failure.get('tb', [])
        message = failure.get('message', "") + "\n" + "\n".join(trace)
        name = failure.get('class')
        module = failure.get('module')

        # NOTE(ameade): We DO NOT want to allow just any module to be imported,
        # in order to prevent arbitrary code execution.
        if (module != _EXCEPTIONS_MODULE and
                module not in allowed_remote_exmods):
            return rpc_exceptions.RemoteError(name,
                                              failure.get('message'),
                                              trace)

        try:
            mod = importutils.import_module(module)
            klass = getattr(mod, name)
            if not issubclass(klass, Exception):
                raise TypeError("Can only deserialize Exceptions")

            failure = klass(*failure.get('args', []),
                            **failure.get('kwargs', {}))
        except (AttributeError, TypeError, ImportError):
            return rpc_exceptions.RemoteError(name,
                                              failure.get('message'),
                                              trace)

        ex_type = type(failure)
        str_override = lambda self: message
        new_ex_type = type(ex_type.__name__ + self._REMOTE_POSTFIX, (ex_type,),
                           {'__str__': str_override,
                            '__unicode__': str_override})
        new_ex_type.__module__ = '%s%s' % (module, self._REMOTE_POSTFIX)
        try:
            # NOTE(ameade): Dynamically create a new exception type and swap it
            # in as the new type for the exception. This only works on user
            # defined Exceptions and not core Python exceptions. This is
            # important because we cannot necessarily change an exception
            # message so we must override the __str__ method.
            failure.__class__ = new_ex_type
        except TypeError:
            # NOTE(ameade): If a core exception then just add the traceback to
            # the first exception argument.
            failure.args = (message,) + failure.args[1:]
        return failure
