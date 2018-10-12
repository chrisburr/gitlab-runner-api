from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import pytest
import tempfile

from gl_runner_api import AuthException, Job, Runner
from gl_runner_api.testing import FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_pending=2)
def test_request_job(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    assert isinstance(runner.request_job(), Job)
    assert isinstance(runner.request_job(), Job)
    assert runner.request_job() is None

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 0
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_request_job_invalid_token(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    runner.request_job()
    runner._token = 'invalid_token'
    with pytest.raises(AuthException):
        runner.request_job()

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_repr(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()
    print(repr(job))
    assert str(job.id) in repr(job)
    assert str(job.token) in repr(job)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_serialise(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()

    as_string = job.dumps()
    job_from_string = Job.loads(as_string)
    assert job == job_from_string

    with tempfile.NamedTemporaryFile() as fp:
        job.dump(fp.name)
        job_from_file = Job.load(fp.name)
    assert job == job_from_file

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_serialise_invalid_version(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()
    serialised_job = json.loads(job.dumps())
    serialised_job[0] = 2
    as_string = json.dumps(serialised_job)

    with pytest.raises(ValueError):
        Job.loads(as_string)

    with tempfile.NamedTemporaryFile(mode='wt') as fp:
        json.dump(as_string, fp)
        fp.flush()
        with pytest.raises(ValueError):
            Job.load(fp.name)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0
