from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from gitlab_runner_api import Runner
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
