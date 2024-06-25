# -*- coding: utf-8 -*-
# Copyright, 2024 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import os
import socket
import sys
import time

import bcrypt
from pyrocumulus.auth import AccessToken

from toxiccore.utils import log, bcrypt_string
from toxicmaster import create_settings_and_connect
from toxicslave import create_settings
from toxicwebui import create_settings as create_settings_ui
from toxicpoller import create_settings as create_settings_poller
from toxicnotifications import (
    create_settings_and_connect as create_settings_output)
from tests import DATA_DIR


SOURCE_DIR = os.path.join(DATA_DIR, '..')
SLAVE_ROOT_DIR = DATA_DIR
MASTER_ROOT_DIR = DATA_DIR
POLLER_ROOT_DIR = DATA_DIR
NOTIFICATIONS_ROOT_DIR = DATA_DIR
SECRETS_ROOT_DIR = DATA_DIR

PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])


toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
if not toxicmaster_conf:
    toxicmaster_conf = os.path.join(MASTER_ROOT_DIR, 'toxicmaster.conf')
    os.environ['TOXICMASTER_SETTINGS'] = toxicmaster_conf

toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
if not toxicslave_conf:
    toxicslave_conf = os.path.join(SLAVE_ROOT_DIR, 'toxicslave.conf')
    os.environ['TOXICSLAVE_SETTINGS'] = toxicslave_conf


toxicpoller_conf = os.environ.get('TOXICPOLLER_SETTINGS')
if not toxicpoller_conf:
    toxicpoller_conf = os.path.join(POLLER_ROOT_DIR, 'toxicpoller.conf')
    os.environ['TOXICPOLLER_SETTINGS'] = toxicpoller_conf

toxicweb_conf = os.environ.get('TOXICWEBUI_SETTINGS')
if not toxicweb_conf:
    toxicweb_conf = os.path.join(DATA_DIR, 'toxicwebui.conf')
    os.environ['TOXICWEBUI_SETTINGS'] = toxicweb_conf

toxicoutput_conf = os.environ.get('TOXICNOTIFICATIONS_SETTINGS')
if not toxicoutput_conf:
    toxicoutput_conf = os.path.join(NOTIFICATIONS_ROOT_DIR,
                                    'toxicnotifications.conf')
    os.environ['TOXICNOTIFICATIONS_SETTINGS'] = toxicoutput_conf

create_settings()
create_settings_and_connect()
create_settings_output()
create_settings_poller()
create_settings_ui()

from toxicmaster.users import User  # noqa f402
from tests.functional import SeleniumBrowser  # noqa f402
from toxicwebui import settings as settings_ui  # noqa f402


def create_browser(context):
    """Creates a new selenium browser using Chrome driver and
    sets it in the behave context.

    :param context: Behave's context."""
    context.browser = SeleniumBrowser()


def quit_browser(context):
    """Quits the selenium browser.

    :param context: Behave's context."""
    context.browser.quit()


async def del_repo(context):
    """Deletes the repositories created in tests."""

    from toxicbuild.common.exchanges import scheduler_action, conn

    from toxicmaster import settings as master_settings
    await conn.connect(**master_settings.RABBITMQ_CONNECTION)

    await scheduler_action.declare()
    await scheduler_action.queue_delete()
    await scheduler_action.connection.disconnect()

    from toxicmaster.repository import Repository as RepoModel

    await RepoModel.drop_collection()


async def create_root_user(context):
    user = User(id=settings_ui.ROOT_USER_ID, username='already-exists',
                email='nobody@nowhere.nada', allowed_actions=['add_user'])
    await user.save(force_insert=True)


async def create_user(context):
    user = User(email='someguy@bla.com', is_superuser=True)
    user.set_password('123')
    await user.save()
    context.user = user
    context.user.id = str(context.user.id)


async def del_user(context):
    await context.user.delete()


def before_all(context):
    start_all()

    create_browser(context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_user(context))
    loop.run_until_complete(create_root_user(context))


def after_feature(context, feature):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_repo(context))

    from toxicintegrations.github import GithubIntegration
    loop.run_until_complete(GithubIntegration.drop_collection())


def after_all(context):
    stop_all()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(del_user(context))
    loop.run_until_complete(User.drop_collection())

    quit_browser(context)


def start_all():
    start_slave()
    start_poller()
    start_master()
    start_notifications()
    start_integrations()
    start_webui()


def stop_all():
    stop_poller()
    stop_master()
    stop_notifications()
    stop_slave()
    stop_integrations()
    stop_webui()


def start_slave(sleep=0.5):
    """Starts an slave server in a new process for tests"""

    toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    toxicslave_cmd = 'toxicslave'
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicslave_cmd, 'start', SLAVE_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicslave_conf:
        cmd += ['-c', toxicslave_conf]

    os.system(' '.join(cmd))


def stop_slave():
    """Stops the test slave"""

    toxicslave_cmd = 'toxicslave'
    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicslave_cmd, 'stop', SLAVE_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_poller():

    toxicpoller_conf = os.environ.get('TOXICPOLLER_SETTINGS')
    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)
    toxicpoller_cmd = 'toxicpoller'
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicpoller_cmd, 'start', POLLER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicpoller_conf:
        cmd += ['-c', toxicpoller_conf]

    os.system(' '.join(cmd))


def stop_poller():

    toxicpoller_cmd = 'toxicpoller'
    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicpoller_cmd, 'stop', POLLER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def wait_master_to_be_alive(root_dir):
    from toxicmaster import settings
    HOST = settings.HOLE_ADDR
    PORT = settings.HOLE_PORT
    alive = False
    limit = int(os.environ.get('FUNCTESTS_MASTER_START_TIMEOUT', 20))
    step = 0.5
    i = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        while not alive and i < limit:
            try:
                s.connect((HOST, PORT))
                s.close()
            except Exception:
                alive = False
            else:
                alive = True
                break

            time.sleep(step)
            i += step

    if not alive:
        log(f'Master did not start at {HOST}:{PORT} in {limit} seconds',
            level='error')
        logfile = os.path.join(root_dir, 'toxicmaster.log')
        os.system(f'tail --lines 100 {logfile}')


def start_master(sleep=0.5):
    """Starts a master server in a new process for tests"""

    toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')

    toxicmaster_cmd = 'toxicmaster'
    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicmaster_cmd, 'start', MASTER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicmaster_conf:
        cmd += ['-c', toxicmaster_conf]

    os.system(' '.join(cmd))

    wait_master_to_be_alive(MASTER_ROOT_DIR)


def stop_master():
    """Stops the master test server"""

    toxicmaster_cmd = 'toxicmaster'
    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicmaster_cmd, 'stop', MASTER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_secrets(sleep=0.5):
    """Starts a secrets server in a new process for tests"""

    toxicsecrets_conf = os.environ.get('TOXICSECRETS_SETTINGS')

    toxicsecrets_cmd = 'toxicsecrets'
    pidfile = 'toxicsecrets{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicsecrets_cmd, 'start', SECRETS_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicsecrets_conf:
        cmd += ['-c', toxicsecrets_conf]

    os.system(' '.join(cmd))


def stop_secrets():
    """Stops the secrets test server"""

    toxicsecrets_cmd = 'toxicsecrets'
    pidfile = 'toxicsecrets{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           toxicsecrets_cmd, 'stop', SECRETS_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_notifications(sleep=0.5):
    """Starts a toxicnotifications instance in a new process for tests"""

    conf = os.path.join(NOTIFICATIONS_ROOT_DIR, 'toxicnotifications.conf')

    cmd = 'toxicnotifications'
    pidfile = 'toxicnotifications{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'start', NOTIFICATIONS_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_notifications():
    """Stops the toxicnotifications test server"""

    cmd = 'toxicnotifications'
    pidfile = 'toxicnotifications{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'stop', NOTIFICATIONS_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_webui(sleep=0.5):
    """Starts a toxicwebui instance in a new process for tests"""

    conf = os.path.join(DATA_DIR, 'toxicwebui.conf')

    cmd = 'toxicwebui'
    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'start', DATA_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_webui():
    """Stops a toxicwebui instance"""

    conf = os.path.join(DATA_DIR, 'toxicwebui.conf')

    cmd = 'toxicwebui'
    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'stop', DATA_DIR,
           '--pidfile', pidfile]

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def start_integrations():
    conf = os.path.join(DATA_DIR, 'toxicintegrations.conf')
    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = 'python ./toxicintegrations/cmds.py '
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'start', DATA_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_integrations():
    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = 'python ./toxicintegrations/cmds.py '
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'stop', DATA_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


async def create_output_access_token():
    from toxicwebui import settings

    real_token = bcrypt_string(settings.ACCESS_TOKEN_BASE, bcrypt.gensalt(8))
    token = AccessToken(token_id=settings.ACCESS_TOKEN_ID,
                        token=real_token)
    await token.save()
