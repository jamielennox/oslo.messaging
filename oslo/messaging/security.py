
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

import abc
import ast

import six
from stevedore import driver

from oslo.messaging._drivers import base
from oslo.messaging import exceptions


class SecureMessage(base.IncomingMessage):
    """Class for wrapping incoming message objects.

    This is used to wrap incoming messages allowing the safe
    use of message.reply to send a secured response back to the
    originator.
    """

    def __init__(self, message, listener, source):
        self._listener = listener
        self._message = message
        self._policy = listener._policy
        self._source = source

    def reply(self, reply=None, failure=None, log_failure=True):
        if reply:
            reply = self._policy.encrypt(self._source, reply)
        self._message.reply(reply, failure, log_failure)

    def requeue(self):
        return self._message.requeue()

    def acknowledge(self):
        return self._message.acknowledge()

    @property
    def conf(self):
        return self._message.conf

    @property
    def listener(self):
        return self._listener

    @property
    def ctxt(self):
        return self._message.ctxt

    @property
    def message(self):
        return self._message.message


class SecureListener(base.Listener):
    """Class for wrapping listener objects.

    This is used to intercept incoming messages for decryption and
    verification. It returns a SecureMessage object allowing the safe
    use of message.reply to send a secured response back to the
    originator.
    """

    def __init__(self, listener, policy):
        self._listener = listener
        self._policy = policy

    def poll(self, timeout=None):
        message = self._listener.poll(timeout=timeout)

        if message:
            source = message.message["sender"]
            body = self._policy.decrypt(message.message)
            message.message = ast.literal_eval(body)
            message = SecureMessage(message, self, source)
        return message


@six.add_metaclass(abc.ABCMeta)
class SecurityPolicyBase(object):
    """Abstract base class for Transport security policies."""

    def __init__(self, conf):
        pass

    @abc.abstractmethod
    def encrypt(self, target, message):
        """Encrypt a message to a given target."""

    @abc.abstractmethod
    def decrypt(self, message):
        """Decrypt a received message."""

    def listen(self, listener):
        """Wrap a Listener to decrypt incoming messages."""
        return SecureListener(listener, self)


class SecurityLoadFailure(exceptions.MessagingException):
    """Raised if a transport security policy can't be loaded."""

    def __init__(self, security, ex):
        msg = 'Failed to load security policy "%s": %s' % (security, ex)
        super(SecurityLoadFailure, self).__init__(msg)
        self.security = security
        self.ex = ex


class SecurityValidityFailure(exceptions.MessagingException):
    """Raised if a message fails security validation."""

    def __init__(self, ex):
        msg = 'Failed to decrypt message: "%s"' % (ex)
        super(SecurityValidityFailure, self).__init__(msg)
        self.ex = ex


def get_security_policy(policy, conf):
    """A factory method for SecurityPolicy objects.

    This method will load and return a security policy plug in given its
    name.

    :param policy: The policy name.
    :param conf: The local configuration details
    :return: a security policy instance.
    """
    try:
        mgr = driver.DriverManager('oslo.messaging.security',
                                   policy,
                                   invoke_args=[conf],
                                   invoke_on_load=True)
    except RuntimeError as ex:
        raise SecurityLoadFailure(policy, ex)

    return mgr.driver