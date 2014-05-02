# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2011 Red Hat, Inc.
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

import copy
import logging

import six

from oslo.messaging.rpc import protocol as rpc_protocol

# FIXME(markmc): remove this
_ = lambda s: s

LOG = logging.getLogger(__name__)

_EXCEPTIONS_MODULE = 'exceptions' if six.PY2 else 'builtins'


class Connection(object):
    """A connection, returned by rpc.create_connection().

    This class represents a connection to the message bus used for rpc.
    An instance of this class should never be created by users of the rpc API.
    Use rpc.create_connection() instead.
    """
    def close(self):
        """Close the connection.

        This method must be called when the connection will no longer be used.
        It will ensure that any resources associated with the connection, such
        as a network connection, and cleaned up.
        """
        raise NotImplementedError()


def _safe_log(log_func, msg, msg_data):
    """Sanitizes the msg_data field before logging."""
    SANITIZE = ['_context_auth_token', 'auth_token', 'new_pass']

    def _fix_passwords(d):
        """Sanitizes the password fields in the dictionary."""
        for k in six.iterkeys(d):
            if k.lower().find('password') != -1:
                d[k] = '<SANITIZED>'
            elif k.lower() in SANITIZE:
                d[k] = '<SANITIZED>'
            elif isinstance(d[k], dict):
                _fix_passwords(d[k])
        return d

    return log_func(msg, _fix_passwords(copy.deepcopy(msg_data)))


class CommonRpcContext(object):
    def __init__(self, **kwargs):
        self.values = kwargs

    def __getattr__(self, key):
        try:
            return self.values[key]
        except KeyError:
            raise AttributeError(key)

    def to_dict(self):
        return copy.deepcopy(self.values)

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def deepcopy(self):
        return self.from_dict(self.to_dict())

    def update_store(self):
        #local.store.context = self
        pass


def serialize_remote_exception(*args, **kwargs):
    """Prepares exception data to be sent over rpc.

    Failure_info should be a sys.exc_info() tuple.

    """
    return rpc_protocol.OpenStackRPC2().serialize_exception(*args, **kwargs)


def deserialize_remote_exception(*args, **kwargs):
    return rpc_protocol.OpenStackRPC2().deserialize_exception(*args, **kwargs)


def serialize_msg(*args, **kwargs):
    return rpc_protocol.OpenStackRPC2().serialize_msg(*args, **kwargs)


def deserialize_msg(*args, **kwargs):
    return rpc_protocol.OpenStackRPC2().deserialize_msg(*args, **kwargs)
