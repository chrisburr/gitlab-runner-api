from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'Job',
]

import json
import re
from traceback import format_exc
try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

import requests
import six

from .exceptions import AlreadyFinishedExcpetion, AuthException
from .failure_reasons import _FailureReason, RunnerSystemFailure, UnknownFailure
from .logging import logger
from .version import CURRENT_DATA_VERSION


class Job(object):
    @classmethod
    def load(cls, filename):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        filename : :obj:`str`
            Path to file that represents the job to initialise.

        Returns
        -------
        :py:class:`Job <gitlab_runner_api.Job>`
        """
        with open(filename, 'rt') as fp:
            return cls.loads(fp.read())

    @classmethod
    def loads(cls, data):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        data : :obj:`str`
            String representing the job to initialise

        Returns
        -------
        :py:class:`Job <gitlab_runner_api.Job>`
        """
        data = json.loads(data)
        version, data = data[0], data[1:]
        if version == 1:
            from .runner import Runner
            runner_info, job_info, state = data
            return cls(Runner.loads(runner_info), job_info,
                       fail_on_error=False, state=state)
        else:
            raise ValueError('Unrecognised data version: '+str(version))

    def __init__(self, runner, job_info, fail_on_error=True, state='running'):
        self._runner = runner
        self._state = 'running'  # All jobs start as running
        self.state = state
        # TODO Create and validate a schema for the job_info dict
        self._job_info = job_info
        try:
            self._parse_job_info()
        except Exception:
            exception_string = format_exc()
            logger.fatal('%s: Failed to parse job %d\'s description\n%s',
                         urlparse(self._runner.api_url).netloc, self.id, exception_string)
            if fail_on_error:
                log = 'gitlab_runner_api failed to parse job description\n'
                log += exception_string
                self.set_failed(RunnerSystemFailure(), log)
            raise

    def _parse_job_info(self):
        self._id = self._job_info['id']

        self._token = self._job_info['token']

        self._variables = []
        for var_info in self._job_info['variables']:
            logger.debug('%s: Parsing environment variable from job %d (%s)',
                         urlparse(self._runner.api_url).netloc, self.id, repr(var_info))
            self._variables.append(EnvVar(**var_info))

    def __repr__(self):
        return 'Job(id={id}, token={token}, state={state})'.format(
            id=self.id, token=self.token, state=self.state
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def dump(self, filename):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        filename : :obj:`str`
            Registration token
        """
        with open(filename, 'wt') as fp:
            fp.write(self.dumps())

    def dumps(self):
        """Serialise this job as a string which can be loaded with with `Job.loads`.

        Returns
        -------
        :obj:`str`
            String representation of the job that can be loaded with
            `Job.loads`
        """
        return json.dumps([CURRENT_DATA_VERSION, self._runner.dumps(),
                           self._job_info, self.state])

    def set_success(self, log=None, artifacts=None):
        self._set_status('success', log, artifacts)

    def set_failed(self, failure_reason=None, log=None, artifacts=None):
        self._set_status('failed', log, artifacts, failure_reason)

    def _set_status(self, state, log, artifacts, failure_reason=None):
        if self.state != 'running':
            raise AlreadyFinishedExcpetion('Job {id} has already finished as {state}'
                                           .format(id=self.id, state=self.state))

        data = {
            'token': self.token,
            'state': state,
        }

        if log is not None:
            if not isinstance(log, six.string_types):
                raise ValueError()
            data['trace'] = log

        if state == 'failed':
            if failure_reason is None:
                failure_reason = UnknownFailure()
            elif not isinstance(failure_reason, _FailureReason):
                raise ValueError()
            data['failure_reason'] = str(failure_reason)

        if artifacts is not None:
            self._upload_artifacts(artifacts)

        response = requests.put(self._runner.api_url+'/api/v4/jobs/'+str(self.id), json=data)

        if response.status_code == 200:
            logger.info('%s: Set job %d as %s',
                        urlparse(response.url).netloc, self.id, state)
        elif response.status_code == 403:
            logger.error('%s: Failed to authenticate job %d with token %s',
                         urlparse(response.url).netloc, self.id, self.token)
            raise AuthException()
        else:
            raise NotImplementedError('Unrecognised status code from request',
                                      response, response.content)

        self.state = state

    def _upload_artifacts(self, artifacts):
        raise NotImplementedError()

    @property
    def id(self):
        return self._id

    @property
    def token(self):
        return self._token

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        if new_state not in ['running', 'success', 'failed']:
            raise ValueError('Invalid state given '+new_state)
        if self.state != 'running':
            raise AlreadyFinishedExcpetion('Status cannot be changed for an '
                                           'already finished job')
        self._state = new_state

    @property
    def variables(self):
        return self._variables


class EnvVar(object):
    """docstring for EnvVar"""
    def __init__(self, key, value, public):
        """

        Raises
        ------
        ValueError: One of the properties are invalid
        """
        if not re.match(r'^[a-zA-Z0-9_]+$', key):
            raise ValueError('Environment variables must match /^[a-zA-Z0-9_]+$/')
        self._key = key

        self._value = value

        if not isinstance(public, bool):
            raise ValueError('Property "public" of EnvVar must be of type bool')
        self._is_public = public

    def __repr__(self):
        if self.is_public:
            ret_val = 'EnvVar(key={key}, value={value})'
        else:
            ret_val = 'EnvVar(key={key})'
        return ret_val.format(key=self.key, value=self.value)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    @property
    def is_public(self):
        return self._is_public
