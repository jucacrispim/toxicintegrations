# -*- coding: utf-8 -*-

# Copyright 2018, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You shoud have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=all

__doc__ = """This package implements toxicbuild integrations with code
hosting services using the oauth2 protocol.

To implement a new integration you must extend the following classes:
:class:`~toxicintegrations.base.BaseIntegration`,
:class:`~toxicintegrations.base.BaseIntegrationApp` and
:class:`~toxicintegrations.webhook_receivers.BaseWebhookReceiver`.

Check the documentation for each class for more information.
"""

from mongomotor import connect
from toxiccore.conf import Settings


__version__ = '0.11.0'

ENVVAR = 'TOXICINTEGRATIONS_SETTINGS'
DEFAULT_SETTINGS = 'toxicintegrations.conf'

settings = None
dbconn = None


def create_settings_and_connect():
    global settings, dbconn

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
    dbsettings = settings.DATABASE
    dbconn = connect(**dbsettings)


async def ensure_indexes():
    from .github import GithubApp, GithubIntegration
    from .gitlab import GitlabApp, GitlabIntegration
    from .bitbucket import BitbucketApp, BitbucketIntegration

    await GithubApp.ensure_indexes()
    await GithubIntegration.ensure_indexes()
    await GitlabApp.ensure_indexes()
    await GitlabIntegration.ensure_indexes()
    await BitbucketApp.ensure_indexes()
    await BitbucketIntegration.ensure_indexes()
