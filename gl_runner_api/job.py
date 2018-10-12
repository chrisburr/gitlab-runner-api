from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json

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
        :py:class:`Job <gl_runner_api.Job>`
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
        :py:class:`Job <gl_runner_api.Job>`
        """
        data = json.loads(data)
        version, data = data[0], data[1:]
        if version == 1:
            from .runner import Runner
            runner_info, job_info = data
            return cls(Runner.loads(runner_info), job_info)
        else:
            raise ValueError('Unrecognised data version: '+str(version))

    def __init__(self, runner, job_info):
        self._runner = runner
        # TODO Create and validate a schema for the job_info dict
        assert 'id' in job_info
        assert 'token' in job_info
        self._job_info = job_info

    def __repr__(self):
        return 'Job(id={id}, token={token})'.format(
            id=self.id, token=self.token
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
        return json.dumps([CURRENT_DATA_VERSION, self._runner.dumps(), self._job_info])

    @property
    def id(self):
        return self._job_info['id']

    @property
    def token(self):
        return self._job_info['token']
