from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gl_runner_api.testing import API_ENDPOINT, FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2)
def test_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/jobs/request', {})
    assert response.status_code == 400
    assert response.json()['error'] == 'token is missing'


@gitlab_api.use(n_runners=2)
def test_invalid_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/jobs/request', {'token': 'an_invalid_token'})
    assert response.status_code == 403
    assert response.json()['message'] == '403 Forbidden'


@gitlab_api.use(n_runners=2)
def test_none_available(gitlab_api):
    runner_token = list(gitlab_api.runners.keys())[0]
    response = requests.post(API_ENDPOINT+'/jobs/request', {'token': runner_token})
    # Check the response
    assert response.status_code == 204
    data = response.json()
    assert data == {}
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 0
    assert len(gitlab_api.running_jobs) == 0
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_runners=2, n_pending=3)
def test_request_job(gitlab_api):
    expected_job = gitlab_api.pending_jobs[0]
    runner_token = list(gitlab_api.runners.keys())[0]
    response = requests.post(API_ENDPOINT+'/jobs/request', {'token': runner_token})
    # Check the response
    assert response.status_code == 201
    data = response.json()
    # TODO: Validate schema
    assert data['job_info']['name'] == expected_job['name']
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 2
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0
