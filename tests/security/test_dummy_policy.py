
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

import mock

from oslo.messaging import security
from tests import utils as test_utils


class TestDummyPolicy(test_utils.BaseTestCase):

    def setUp(self):
        super(TestDummyPolicy, self).setUp()
        self.policy = security.get_security_policy("dummy", None)

    def test_dummy_encrypt(self):
        sec = self.policy.encrypt("target", "test")
        self.assertEqual("test", sec["message"])
        sec = self.policy.decrypt(sec)
        self.assertEqual("test", sec)

    def test_dummy_listen(self):
        moc = mock.MagicMock()
        sec = self.policy.listen(moc)
        self.assertEqual(moc, sec._listener)
        self.assertEqual(self.policy, sec._policy)