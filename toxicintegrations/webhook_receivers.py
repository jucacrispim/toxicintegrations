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

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from asyncio import ensure_future
import base64
import json
from pyrocumulus.web.applications import PyroApplication
from pyrocumulus.web.decorators import post, get
from pyrocumulus.web.handlers import BasePyroHandler, PyroRequest
from pyrocumulus.web.urlmappers import URLSpec
from tornado.web import HTTPError
from toxiccommon.interfaces import UserInterface
from toxiccore.utils import LoggerMixin, validate_string
from toxicintegrations import settings
from toxicintegrations.bitbucket import (BitbucketIntegration,
                                         BitbucketApp)
from toxicintegrations.github import (GithubIntegration, GithubApp,
                                      BadSignature)
from toxicintegrations.gitlab import GitlabIntegration, GitlabApp


class BaseWebhookReceiver(LoggerMixin, BasePyroHandler):

    APP_CLS = None
    INSTALL_CLS = None
    _tasks = set()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = None
        self.params = None
        self.body = None
        self.events = {'push': self.handle_push,
                       'merge_request': self.handle_pull_request}

    def check_event_type(self):
        raise NotImplementedError

    def get_repo_external_id(self):
        raise NotImplementedError

    def get_pull_request_source(self):
        raise NotImplementedError

    def get_pull_request_target(self):
        raise NotImplementedError

    def get_request_signature(self):
        raise NotImplementedError

    async def validate_webhook(self):
        token = self.get_request_signature()
        app = await self.APP_CLS.get_app()
        try:
            await app.validate_token(token)
        except BadSignature:
            raise HTTPError(403)
        return True

    def prepare(self):
        self.params = PyroRequest(self.request.arguments)
        self._parse_body()
        self.event_type = self.check_event_type()

    @get('hello')
    def hello(self):
        return {'code': 200, 'msg': 'Hi there!'}

    def create_installation(self, user):
        code = self.params.get('code')
        if not code:
            raise HTTPError(400)

        return ensure_future(self.INSTALL_CLS.create(user, code=code))

    async def get_install(self):
        install_id = self.params.get('installation_id')
        install = await self.INSTALL_CLS.objects.get(id=install_id)
        return install

    @post('webhooks')
    async def receive_webhook(self):

        await self.validate_webhook()

        async def default_call():
            raise HTTPError(400, 'What was that? {}'.format(self.event_type))

        call = self.events.get(self.event_type, default_call)
        self.log('event_type {} received'.format(self.event_type))
        await call()
        msg = '{} handled successfully'.format(self.event_type)
        return {'code': 200, 'msg': msg}

    async def handle_push(self):
        external_id = self.get_repo_external_id()
        install = await self.get_install()
        t = ensure_future(install.update_repository(external_id))
        type(self)._tasks.add(t)
        t.add_done_callback(  # pragma no cover
            lambda t: type(self)._tasks.remove(t))
        return 'updating repo'

    async def handle_pull_request(self):
        install = await self.get_install()
        source = self.get_pull_request_source()
        target = self.get_pull_request_target()

        repo_branches = {source['branch']: {
            'notify_only_latest': True,
            'builders_fallback': target['branch']}
        }
        self.log(f'Pull request source: {source}', level='debug')
        self.log(f'Pull request target: {target}', level='debug')
        if source['id'] != target['id']:
            external = {'url': source['url'],
                        'name': source['name'],
                        'branch': source['branch'],
                        'into': target['branch']}

            self.log(f'External pull request {external}', level='debug')
            await install.update_repository(target['id'], external=external,
                                            repo_branches=repo_branches)
        else:
            self.log('Pull request', level='debug')
            await install.update_repository(target['id'],
                                            repo_branches=repo_branches)

    @get('setup')
    async def setup(self):
        user = await self._get_user_from_cookie()
        if not user:
            url = '{}?redirect={}'.format(
                settings.TOXICUI_LOGIN_URL, self.request.full_url())
        else:
            self.create_installation(user)
            url = settings.TOXICUI_URL

        return self.redirect(url)

    async def _get_user_from_cookie(self):
        cookie = self.get_secure_cookie(settings.TOXICUI_COOKIE)
        if not cookie:
            self.log('No cookie found.', level='debug')
            return

        user_dict = json.loads(base64.decodebytes(cookie).decode('utf-8'))
        user = await UserInterface.get(id=user_dict['id'])
        return user

    def _parse_body(self):
        if self.request.body:
            self.body = json.loads(self.request.body.decode())


class BitbucketWebhookReceiver(BaseWebhookReceiver):

    APP_CLS = BitbucketApp
    INSTALL_CLS = BitbucketIntegration

    def check_event_type(self):
        return self.request.headers.get('X-Event-Key')

    def get_request_signature(self):
        return self.params.get('token')

    def get_external_id(self):
        return self.body['repository']['uuid']

    def get_pull_request_source(self):
        attrs = self.body['source']
        return {'name': attrs['repository']['name'],
                'id': attrs['repository']['uuid'],
                'branch': attrs['branch'],
                # no url in repo payloads. This not work with
                # pr from other repos
                'url': None}

    def get_pull_request_target(self):
        attrs = self.body['target']
        return {'name': attrs['repository']['name'],
                'id': attrs['repository']['uuid'],
                'branch': attrs['branch'],
                # no url in repo payloads. This not work with
                # pr from other repos
                'url': None}


class GitlabWebhookReceiver(BaseWebhookReceiver):

    APP_CLS = GitlabApp
    INSTALL_CLS = GitlabIntegration

    def check_event_type(self):
        body = self.body or {}
        return body.get('object_kind')

    def state_is_valid(self):
        """Checks if the state hash sent by gitlab is valid.
        """

        state = self.params.get('state')
        if not state:
            raise HTTPError(400)

        secret = settings.TORNADO_OPTS['cookie_secret']

        return validate_string(state, secret)

    def create_installation(self, user):
        if not self.state_is_valid():
            raise HTTPError(400)

        return super().create_installation(user)

    def get_repo_external_id(self):
        return self.body['project']['id']

    def get_request_signature(self):
        return self.request.headers.get('X-Gitlab-Token')

    def get_pull_request_source(self):
        attrs = self.body['object_attributes']
        return {'name': attrs['source']['name'],
                'id': attrs['source_project_id'],
                'branch': attrs['source_branch'],
                'url': attrs['source']['git_http_url']}

    def get_pull_request_target(self):
        attrs = self.body['object_attributes']
        return {'name': attrs['target']['name'],
                'id': attrs['target_project_id'],
                'branch': attrs['target_branch'],
                'url': attrs['target']['git_http_url']}


class GithubWebhookReceiver(BaseWebhookReceiver):

    APP_CLS = GithubApp

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        handle_repo_removed = self._handle_install_repo_removed
        handle_repo_added = self._handle_install_repo_added
        self.events = {
            'ping': self._handle_ping,
            'push': self.handle_push,
            'repository-create': self._handle_install_repo_added,
            'pull_request-opened': self.handle_pull_request,
            'pull_request-synchronize': self.handle_pull_request,
            'check_run-rerequested': self._handle_check_run_rerequested,
            'installation-deleted': self._handle_install_deleted,
            'installation_repositories-removed': handle_repo_removed,
            'installation_repositories-added': handle_repo_added}

    def create_installation(self, user):
        githubapp_id = self.params.get('installation_id')
        if not githubapp_id:
            raise HTTPError(400)

        ensure_future(GithubIntegration.create(
            user, github_id=githubapp_id))

    async def _handle_ping(self):  # pragma no cover
        msg = 'Ping received. App id {}\n'.format(self.body['app_id'])
        msg += 'zen: {}'.format(self.body['zen'])
        self.log(msg, level='debug')
        return 'Got it.'

    async def get_install(self):
        install_id = self.body['installation']['id']
        install = await GithubIntegration.objects.get(github_id=install_id)
        return install

    def get_repo_external_id(self):
        repo_github_id = self.body['repository']['id']
        return repo_github_id

    async def _handle_install_repo_added(self):
        install = await self.get_install()
        tasks = []
        for repo_info in self.body['repositories_added']:
            t = ensure_future(self._get_and_import_repo(
                install, repo_info['full_name']))
            tasks.append(t)

        return tasks

    async def _get_and_import_repo(self, install, repo_full_name):
        repo_full_info = await install.get_repo(repo_full_name)
        await install.import_repository(repo_full_info)

    async def _handle_install_repo_removed(self):
        install = await self.get_install()
        for repo_info in self.body['repositories_removed']:
            ensure_future(install.remove_repository(repo_info['id']))

    def get_pull_request_source(self):
        head = self.body['pull_request']['head']
        source = {'id': head['repo']['id'],
                  'url': head['repo']['clone_url'],
                  'name': head['label'],
                  'branch': head['ref']}
        return source

    def get_pull_request_target(self):
        base = self.body['pull_request']['base']
        source = {'id': base['repo']['id'],
                  'branch': base['ref']}
        return source

    async def _handle_check_run_rerequested(self):
        install = await self.get_install()
        check_suite = self.body['check_run']['check_suite']
        repo_id = self.body['repository']['id']
        branch = check_suite['head_branch']
        named_tree = check_suite['head_sha']
        ensure_future(install.repo_request_build(repo_id, branch, named_tree))

    async def _handle_install_deleted(self):
        install = await self.get_install()
        user = UserInterface(None, {'id': install.user_id})
        await install.delete(user)

    async def validate_webhook(self):
        signature = self.request.headers.get('X-Hub-Signature')
        app = await GithubApp.get_app()

        try:
            app.validate_token(signature, self.request.body)
        except BadSignature:
            raise HTTPError(403, 'Bad signature')

    def check_event_type(self):
        event_type = self.request.headers.get('X-GitHub-Event')

        if not event_type:
            msg = 'No event type\n{}'.format(self.body)
            self.log(msg, level='warning')

        action = self.body.get('action') if self.body else None
        if action:
            event_type = '{}-{}'.format(event_type, action)
        return event_type


gh_url = URLSpec('/github/(.*)', GithubWebhookReceiver)
gl_url = URLSpec('/gitlab/(.*)', GitlabWebhookReceiver)
bb_url = URLSpec('/bitbucket/(.*)', BitbucketWebhookReceiver)
app = PyroApplication([gh_url, gl_url, bb_url])
