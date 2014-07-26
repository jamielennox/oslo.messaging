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
from tests import utils as test_utils


class TestListenerWrapper(test_utils.BaseTestCase):

    class FakeMessage(object):
        def __init__(self):
            self.message = {
                "sender": "TestSender",
                "body": "'TestBody'",
                "signature": "TestSig",
                "esek": "TestEsek"
            }

        def reply(self, msg, failure, log_failure):
            self._reply = msg

    class FakeListener(object):
        def poll(self, timeout):
            message = TestListenerWrapper.FakeMessage()
            return message

    class FakePolicy(security.SecurityPolicyBase):
        def __init__(self, identity):
            super(TestListenerWrapper.FakePolicy, self).__init__(identity)

        def encrypt(self, target, message):
            return "safe:" + message

        def decrypt(self, message):
            return message["body"]

        def listen(self, listener):
            return security.SecureListener(listener, self)

    def setUp(self):
        super(TestListenerWrapper, self).setUp()
        self.policy = TestListenerWrapper.FakePolicy("testing")

    def test_listen(self):
        wrapper = self.policy.listen(TestListenerWrapper.FakeListener())
        message = wrapper.poll()

        self.assertEqual(message._policy, self.policy)
        self.assertEqual(message._source, "TestSender")
        self.assertEqual(message.message, "TestBody")

    def test_reply(self):
        wrapper = self.policy.listen(TestListenerWrapper.FakeListener())
        message = wrapper.poll()
        message.reply("testing", False)

        self.assertEqual(message._message._reply, "safe:testing")
