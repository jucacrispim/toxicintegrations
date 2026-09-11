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

from toxiccore.utils import log, bcrypt_string
from toxicintegrations import create_settings_and_connect
import toxicintegrations
from toxicnotifications import (
    create_settings_and_connect as create_settings_output)
from tests import DATA_DIR


_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


SOURCE_DIR = os.path.join(DATA_DIR, '..')
SLAVE_ROOT_DIR = DATA_DIR
MASTER_ROOT_DIR = DATA_DIR
POLLER_ROOT_DIR = DATA_DIR
NOTIFICATIONS_ROOT_DIR = DATA_DIR
SECRETS_ROOT_DIR = DATA_DIR

PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])


# ---------------------------------------------------------------------------
# Server binaries
#
# Each server runs on its own virtualenv so that dependency conflicts do not
# affect each other (or the integrations venv). The binary for a given server is
# resolved in the following order:
#   1. $TOXIC<PROJECT>_BIN        (explicit path, used on CI)
#   2. ~/.virtualenvs/<project>-staging/bin/<cmd>   (local staging env)
#   3. <cmd>                      (plain command on PATH)
# ---------------------------------------------------------------------------


def _venv_bin_dir(project):
    return os.path.join(os.path.expanduser('~'), '.virtualenvs',
                        '{}-staging'.format(project), 'bin')


def _get_cmd(project, cmd):
    """Returns the path of a server command, preferring a dedicated staging
    virtualenv. See the module docstring above for the resolution order."""

    envvar = 'TOXIC{}_BIN'.format(project.upper())
    binpath = os.environ.get(envvar)
    if binpath:
        return os.path.expanduser(binpath)

    full = os.path.join(_venv_bin_dir(project), cmd)
    if os.path.exists(full):
        return full

    return cmd


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

create_settings_and_connect()
create_settings_output()

settings = toxicintegrations.settings

from tests.functional import SeleniumBrowser  # noqa f402


def create_browser(context):
    """Creates a new selenium browser using Chrome driver and
    sets it in the behave context.

    :param context: Behave's context."""
    context.browser = SeleniumBrowser()


def quit_browser(context):
    """Quits the selenium browser.

    :param context: Behave's context."""
    context.browser.quit()


class Requester:
    """A minimal requester for the interfaces."""

    def __init__(self, id, email='someguy@bla.com'):
        self.id = id
        self.email = email


async def get_db():
    from mongomotor.connection import get_connection
    conn = get_connection()
    return conn[os.environ.get('DBNAME', 'toxicintegrations-test')]


async def del_repo(context):
    """Deletes the repositories created in tests."""

    from toxiccommon.exchanges import scheduler_action, conn

    await conn.connect(**settings.RABBITMQ_CONNECTION)

    await scheduler_action.declare()
    await scheduler_action.queue_delete()
    await scheduler_action.connection.disconnect()

    db = await get_db()
    await db['repository'].drop()


async def create_root_user(context):
    from bson.objectid import ObjectId

    db = await get_db()
    coll = db['user']
    doc = await coll.find_one({'_id': ObjectId(settings.ROOT_USER_ID)})
    if doc:
        return

    await coll.insert_one({
        '_id': ObjectId(settings.ROOT_USER_ID),
        'email': 'nobody@nowhere.nada',
        'username': 'already-exists',
        'allowed_actions': ['add_user'],
        'organizations': [],
        'member_of': [],
    })


async def create_user(context):
    import bcrypt
    from bson.objectid import ObjectId

    db = await get_db()
    coll = db['user']
    password = bcrypt_string('123', bcrypt.gensalt(8))
    user_id = ObjectId()
    await coll.insert_one({
        '_id': user_id,
        'email': 'someguy@bla.com',
        'username': 'someguy',
        'password': password,
        'is_superuser': True,
        'allowed_actions': ['add_user', 'add_repo', 'add_slave',
                            'remove_user', 'remove_repo', 'remove_slave'],
        'organizations': [],
        'member_of': [],
    })
    context.user = Requester(user_id)


async def del_user(context):
    db = await get_db()
    await db['user'].delete_many({'username': 'someguy'})


def before_all(context):
    start_all()

    create_browser(context)

    _LOOP.run_until_complete(create_user(context))
    _LOOP.run_until_complete(create_root_user(context))


def after_feature(context, feature):
    _LOOP.run_until_complete(del_repo(context))

    from toxicintegrations.github import GithubIntegration
    _LOOP.run_until_complete(GithubIntegration.drop_collection())


def after_all(context):
    stop_all()
    _LOOP.run_until_complete(del_user(context))

    async def drop_users():
        db = await get_db()
        await db['user'].drop()
    _LOOP.run_until_complete(drop_users())

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
    cmd = [_get_cmd('slave', 'toxicslave'), 'start', SLAVE_ROOT_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicslave_conf:
        cmd += ['-c', toxicslave_conf]

    os.system(' '.join(cmd))


def stop_slave():
    """Stops the test slave"""

    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('slave', 'toxicslave'), 'stop', SLAVE_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_poller():

    toxicpoller_conf = os.environ.get('TOXICPOLLER_SETTINGS')
    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('poller', 'toxicpoller'), 'start', POLLER_ROOT_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicpoller_conf:
        cmd += ['-c', toxicpoller_conf]

    os.system(' '.join(cmd))


def stop_poller():

    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('poller', 'toxicpoller'), 'stop', POLLER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def wait_master_to_be_alive(root_dir):
    from toxicintegrations import settings
    HOST = settings.HOLE_HOST
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

    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('master', 'toxicmaster'), 'start', MASTER_ROOT_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicmaster_conf:
        cmd += ['-c', toxicmaster_conf]

    os.system(' '.join(cmd))

    wait_master_to_be_alive(MASTER_ROOT_DIR)


def stop_master():
    """Stops the master test server"""

    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)

    cmd = [_get_cmd('master', 'toxicmaster'), 'stop', MASTER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_secrets(sleep=0.5):
    """Starts a secrets server in a new process for tests"""

    toxicsecrets_conf = os.environ.get('TOXICSECRETS_SETTINGS')

    pidfile = 'toxicsecrets{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('secrets', 'toxicsecrets'), 'start', SECRETS_ROOT_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicsecrets_conf:
        cmd += ['-c', toxicsecrets_conf]

    os.system(' '.join(cmd))


def stop_secrets():
    """Stops the secrets test server"""

    pidfile = 'toxicsecrets{}.pid'.format(PYVERSION)

    cmd = [_get_cmd('secrets', 'toxicsecrets'), 'stop', SECRETS_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_notifications(sleep=0.5):
    """Starts a toxicnotifications instance in a new process for tests"""

    conf = os.path.join(NOTIFICATIONS_ROOT_DIR, 'toxicnotifications.conf')

    pidfile = 'toxicnotifications{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'toxicnotifications', 'start', NOTIFICATIONS_ROOT_DIR,
           '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_notifications():
    """Stops the toxicnotifications test server"""

    pidfile = 'toxicnotifications{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'toxicnotifications', 'stop', NOTIFICATIONS_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def start_webui(sleep=0.5):
    """Starts a toxicwebui instance in a new process for tests"""

    conf = os.path.join(DATA_DIR, 'toxicwebui.conf')

    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('webui', 'toxicwebui'), 'start', DATA_DIR,
           '--daemonize', '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_webui():
    """Stops a toxicwebui instance"""

    conf = os.path.join(DATA_DIR, 'toxicwebui.conf')

    pidfile = 'toxicwebui{}.pid'.format(PYVERSION)
    cmd = [_get_cmd('webui', 'toxicwebui'), 'stop', DATA_DIR,
           '--pidfile', pidfile]

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def start_integrations():
    conf = os.path.join(DATA_DIR, 'toxicintegrations.conf')
    pidfile = 'toxicintegrations{}.pid'.format(PYVERSION)
    cmd = 'python ./toxicintegrations/cmds.py '
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'start', DATA_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))


def stop_integrations():
    pidfile = 'toxicintegrations{}.pid'.format(PYVERSION)
    cmd = 'python ./toxicintegrations/cmds.py '
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           cmd, 'stop', DATA_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))

