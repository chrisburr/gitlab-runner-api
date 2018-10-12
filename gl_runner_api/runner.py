from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

import requests
import six

from .exceptions import AuthException
from .job import Job
from .logging import logger
from .version import CURRENT_DATA_VERSION


class Runner(object):
    @classmethod
    def register(cls, api_url, token, description=None, active=None, locked=None,
                 run_untagged=None, tags=None, maximum_timeout=None,
                 name=None, version=None, revision=None, platform=None,
                 architecture=None, executor=None):
        """Register a new runner in GitLab.

        Parameters
        ----------
        api_url : :obj:`str`
            URL for accessing the GitLab API
        token : :obj:`str`
            Registration token
        description : :obj:`str`, optional
            Runner's description
        active : :obj:`str`, optional
            Should Runner be active
        locked : :obj:`bool`, optional
            Should Runner be locked for current project
        run_untagged : :obj:`bool`, optional
            Should Runner handle untagged jobs
        tags : :obj:`list` of :obj:`str`, optional
            List of Runner's tags
        maximum_timeout : :obj:`int`, optional
            Maximum timeout set when this Runner will handle the job (in seconds)
        name : :obj:`str`, optional
            The runner's name
        version : :obj:`str`, optional
            The runner's version
        revision : :obj:`str`, optional
            The runner's revision
        platform : :obj:`str`, optional
            The runner's platform
        architecture : :obj:`str`, optional
            The runner's architecture
        executor : :obj:`str`, optional
            The runner's executor

        Returns
        -------
        :py:class:`Runner <gl_runner_api.Runner>`
        """
        if not isinstance(token, six.string_types):
            raise ValueError('token must a string')
        data = {
            'token': token,
            'info': {},
        }
        if description is not None:
            if not isinstance(description, six.string_types):
                raise ValueError('description must a string')
            data['description'] = description
        if active is not None:
            if not isinstance(active, bool):
                raise ValueError('active must a bool')
            data['active'] = active
        if locked is not None:
            if not isinstance(locked, bool):
                raise ValueError('locked must a bool')
            data['locked'] = locked
        if run_untagged is not None:
            if not isinstance(run_untagged, bool):
                raise ValueError('run_untagged must a bool')
            data['run_untagged'] = run_untagged
        if tags is not None:
            if not isinstance(tags, list):
                raise ValueError('tags must a list')
            if not all(isinstance(t, six.string_types) and ',' not in t for t in tags):
                raise ValueError('tags all not contain ","')
            data['tag_list'] = ','.join(tags)
        if maximum_timeout is not None:
            if not isinstance(maximum_timeout, six.integer_types):
                raise ValueError('maximum_timeout must an int')
            data['maximum_timeout'] = maximum_timeout
        # Add runner info attributes
        if name is not None:
            if not isinstance(name, six.string_types):
                raise ValueError('name must a string')
            data['info']['name'] = name
        if version is not None:
            if not isinstance(version, six.string_types):
                raise ValueError('version must a string')
            data['info']['version'] = version
        if revision is not None:
            if not isinstance(revision, six.string_types):
                raise ValueError('revision must a string')
            data['info']['revision'] = revision
        if platform is not None:
            if not isinstance(platform, six.string_types):
                raise ValueError('platform must a string')
            data['info']['platform'] = platform
        if architecture is not None:
            if not isinstance(architecture, six.string_types):
                raise ValueError('architecture must a string')
            data['info']['architecture'] = architecture
        if executor is not None:
            if not isinstance(executor, six.string_types):
                raise ValueError('executor must a string')
            data['info']['executor'] = executor

        request = requests.post(api_url+'/api/v4/runners/',
                                json=data)
        if request.status_code == 201:
            runner_id = int(request.json()['id'])
            runner_token = request.json()['token']
            logger.info('%s: Successfully registered runner %d (%s)',
                        urlparse(request.url).netloc, runner_id, runner_token)
        elif request.status_code == 403:
            logger.error('%s: Failed to register runner using token %s',
                         urlparse(request.url).netloc, token)
            raise AuthException()
        else:
            raise NotImplementedError('Unrecognised status code from request', request, request.content)

        # Remove attributes from the request which shouldn't be stored
        del data['token']
        if 'active' in data:
            del data['active']

        return cls(api_url, runner_id, runner_token, data)

    @classmethod
    def load(cls, filename):
        """Serialise this runner as a file which can be loaded with `Runner.load`.

        Parameters
        ----------
        filename : :obj:`str`
            Path to file that represents the runner to initialise.

        Returns
        -------
        :py:class:`Runner <gl_runner_api.Runner>`
        """
        with open(filename, 'rt') as fp:
            return cls.loads(fp.read())

    @classmethod
    def loads(cls, data):
        """Serialise this runner as a file which can be loaded with `Runner.load`.

        Parameters
        ----------
        data : :obj:`str`
            String representing the runner to initialise

        Returns
        -------
        :py:class:`Runner <gl_runner_api.Runner>`
        """
        data = json.loads(data)
        version, data = data[0], data[1:]
        if version == 1:
            return cls(*data)
        else:
            raise ValueError('Unrecognised data version: '+str(version))

    def __init__(self, api_url, runner_id, runner_token, data):
        self._api_url = api_url
        self._id = runner_id
        self._token = runner_token
        self._data = data

        request = requests.post(self.api_url+'/api/v4/runners/verify',
                                json={'token': self.token})
        if request.status_code == 200:
            logger.info('%s: Successfully initialised runner %d',
                        urlparse(request.url).netloc, self.id)
        elif request.status_code == 403:
            logger.error('%s: Failed to authenticate runner %d with token %s',
                         urlparse(request.url).netloc, self.id, self.token)
            raise AuthException()
        else:
            raise NotImplementedError('Unrecognised status code from request', request, request.content)

    def dump(self, filename):
        """Serialise this runner as a file which can be loaded with `Runner.load`

        Parameters
        ----------
        filename : :obj:`str`
            Registration token
        """
        with open(filename, 'wt') as fp:
            fp.write(self.dumps())

    def dumps(self):
        """Serialise this runner as a string which can be loaded with with `Runner.loads`.

        Returns
        -------
        :obj:`str`
            String representation of the job that can be loaded with
            `Runner.loads`
        """
        return json.dumps([CURRENT_DATA_VERSION, self.api_url, self.id, self.token, self._data])

    def request_job(self):
        """Request a new job to run.

        Returns
        -------
        :py:class:`Job <gl_runner_api.Job>` or None
        """
        request = requests.post(self.api_url+'/api/v4/jobs/request',
                                json={'token': self.token, 'info': self._info})
        if request.status_code == 201:
            logger.info('%s: Got a job %d',
                        urlparse(request.url).netloc, self.id)
            return Job(self, request.json())
        elif request.status_code == 204:
            logger.error('%s: No jobs available %d with token %s',
                         urlparse(request.url).netloc, self.id, self.token)
            return None
        elif request.status_code == 403:
            logger.error('%s: Failed to authenticate runner %d with token %s',
                         urlparse(request.url).netloc, self.id, self.token)
            raise AuthException()
        else:
            raise NotImplementedError('Unrecognised status code from request',
                                      request, request.content)

    def __repr__(self):
        return 'Runner(id={id}, token={token})'.format(
            id=self.id, token=self.token
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def _info(self):
        return self._data['info']

    @property
    def api_url(self):
        return self._api_url

    @property
    def id(self):
        return self._id

    @property
    def token(self):
        return self._token

    @property
    def name(self):
        if 'name' not in self._info:
            return None
        return self._info['name']

    @property
    def description(self):
        if 'description' not in self._data:
            return None
        return self._data['description']

    @property
    def active(self):
        raise NotImplementedError('This should probably be taken from the main API')

    @property
    def locked(self):
        if 'locked' not in self._data:
            return None
        return self._data['locked']

    @property
    def run_untagged(self):
        if 'run_untagged' not in self._data:
            return None
        return self._data['run_untagged']

    @property
    def tags(self):
        if 'tag_list' not in self._data:
            return []
        return set(self._data['tag_list'].split(','))

    @property
    def maximum_timeout(self):
        if 'maximum_timeout' not in self._data:
            return None
        return self._data['maximum_timeout']

    @property
    def version(self):
        if 'version' not in self._info:
            return None
        return self._info['version']

    @property
    def revision(self):
        if 'revision' not in self._info:
            return None
        return self._info['revision']

    @property
    def platform(self):
        if 'platform' not in self._info:
            return None
        return self._info['platform']

    @property
    def architecture(self):
        if 'architecture' not in self._info:
            return None
        return self._info['architecture']

    @property
    def executor(self):
        if 'executor' not in self._info:
            return None
        return self._info['executor']
