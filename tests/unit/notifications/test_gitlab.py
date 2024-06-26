# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from toxicintegrations.gitlab import GitlabIntegration
from toxicintegrations.notifications import gitlab

from tests import async_test


class GitlabCommitStatusNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        self.installation = GitlabIntegration(
            external_user_id=1234, user_id=str(uuid4()),
            user_name='zé')
        await self.installation.save()

        await self.installation.save()
        self.notif = gitlab.GitlabCommitStatusNotification(
            installation=self.installation)

    @async_test
    async def tearDown(self):
        await GitlabIntegration.drop_collection()

    @async_test
    async def test_run(self):
        info = {'status': 'fail', 'id': 'some-id',
                'repository': {'id': 'some-repo-id'}}
        self.notif._send_message = AsyncMock(
            spec=self.notif._send_message)

        await self.notif.run(info)
        self.assertTrue(self.notif._send_message.called)

    @patch.object(GitlabIntegration, 'get_headers', AsyncMock(
        spec=GitlabIntegration.get_headers))
    @patch.object(gitlab.requests, 'post', AsyncMock(
        spec=gitlab.requests.post))
    @async_test
    async def test_send_message(self):
        self.notif.sender = {'id': 'some-id',
                             'full_name': 'bla/ble',
                             'external_full_name': 'ble/ble'}
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'status': 'exception',
                         'id': 'some-id'}

        ret = MagicMock()
        ret.text = ''
        ret.status = 201
        gitlab.requests.post.return_value = ret

        await self.notif._send_message(buildset_info)
        self.assertTrue(gitlab.requests.post.called)
