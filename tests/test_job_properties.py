from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from gitlab_runner_api import AlreadyFinishedExcpetion, Runner
from gitlab_runner_api.testing import FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_pending=2)
def test_id(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()
    assert job.id == int(gitlab_api.running_jobs[0].id)


@gitlab_api.use(n_pending=2)
def test_token(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()
    assert job.token == gitlab_api.running_jobs[0].token


@gitlab_api.use(n_pending=4)
def test_set_state(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)

    job = runner.request_job()
    assert job.state == 'running'

    with pytest.raises(ValueError):
        job.state = 'badstate'
    assert job.state == 'running'

    job.state = 'success'
    assert job.state == 'success'

    with pytest.raises(AlreadyFinishedExcpetion):
        job.state = 'running'
    assert job.state == 'success'

    with pytest.raises(AlreadyFinishedExcpetion):
        job.state = 'success'
    assert job.state == 'success'

    with pytest.raises(AlreadyFinishedExcpetion):
        job.state = 'failed'
    assert job.state == 'success'

    with pytest.raises(ValueError):
        job.state = 'badstate'


@gitlab_api.use(n_pending=2)
def test_variables(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    job = runner.request_job()

    api_variables = gitlab_api.running_jobs[0].as_dict()['variables']
    assert len(api_variables) == len(job.variables)
    for api_var, package_var in zip(api_variables, job.variables):
        assert api_var['key'] == package_var.key
        assert api_var['value'] == package_var.value
        assert api_var['public'] is package_var.is_public
