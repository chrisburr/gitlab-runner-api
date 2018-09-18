from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gl_runner_api.testing import API_ENDPOINT, FakeGitlabAPI, test_log


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_update_log_only(gitlab_api):
    job = gitlab_api.running_jobs[1]

    # Update the log text once
    data = {
        'token': job.token,
        'trace': 'Initial log text',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+job.id, data)
    # Check the response
    assert response.status_code == 200
    assert response.json() is None
    gitlab_api.running_jobs[1].log = 'Initial log text'

    # Update the log text again
    data = {
        'token': job.token,
        'trace': test_log,
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+job.id, data)
    # Check the response
    assert response.status_code == 200
    assert response.json() is None
    gitlab_api.running_jobs[1].log = test_log

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_set_success(gitlab_api):
    job = gitlab_api.running_jobs[1]
    data = {
        'token': job.token,
        'trace': test_log,
        'state': 'success',
        'failure_reason': 'script_failure',  # This should be ignored
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+job.id, data)
    # Check the response
    assert response.status_code == 200
    assert response.json() is True
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 3
    assert len(gitlab_api.completed_jobs) == 1
    assert gitlab_api.completed_jobs[0].id == job.id
    assert gitlab_api.completed_jobs[0].status == 'success'
    assert gitlab_api.completed_jobs[0].log == test_log
    assert gitlab_api.completed_jobs[0].failure_reason is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_set_failed(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]
    data = {
        'token': expected_job.token,
        'trace': test_log,
        'state': 'failed',
        'failure_reason': 'script_failure',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 200
    assert response.json() is True
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 3
    assert len(gitlab_api.completed_jobs) == 1
    assert gitlab_api.completed_jobs[0].status == 'failed'
    assert gitlab_api.completed_jobs[0].log == test_log
    assert gitlab_api.completed_jobs[0].failure_reason == 'script_failure'


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_invalid_state(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]
    data = {
        'token': expected_job.token,
        'trace': test_log,
        'state': 'invalid_state',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 200
    assert response.json() is None
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    assert gitlab_api.running_jobs[1].log == test_log


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4, n_success=1, n_failed=2)
def test_already_finished(gitlab_api):
    for job in gitlab_api.completed_jobs:
        data = {
            'token': job.token,
            'trace': test_log,
            'state': 'success',
            'failure_reason': 'script_failure',  # This should be ignored
        }
        response = requests.put(API_ENDPOINT+'/jobs/'+job.id, data)
        # Check the response
        assert response.status_code == 403
        assert response.json() == {'message': '403 Forbidden  - Job is not running'}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 3


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_auth_error(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]

    # Request with no token
    data = {
        'trace': test_log,
        'state': 'success',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 400, response.json()
    assert response.json() == {'error': 'token is missing'}

    # Request with invalid token
    data = {
        'token': 'invalid_token',
        'trace': test_log,
        'state': 'success',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 403, response.json()
    assert response.json() == {'message': '403 Forbidden'}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        j.log = ''


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_invalid_failure_reason(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]

    # Request with invalid token
    data = {
        'token': 'invalid_token',
        'trace': test_log,
        'state': 'success',
        'failure_reason': 'invalid_reason',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 400
    assert response.json() == {'error': 'failure_reason does not have a valid value'}

    # Otherwise valid request
    data = {
        'token': expected_job.token,
        'trace': test_log,
        'state': 'success',
        'failure_reason': 'invalid_reason',
    }
    response = requests.put(API_ENDPOINT+'/jobs/'+expected_job.id, data)
    # Check the response
    assert response.status_code == 400
    assert response.json() == {'error': 'failure_reason does not have a valid value'}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        j.log = ''
