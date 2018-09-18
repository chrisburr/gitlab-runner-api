from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gl_runner_api.testing import FakeGitlabAPI, API_ENDPOINT


gitlab_api = FakeGitlabAPI()


@gitlab_api.use()
def test_register_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/runners/', {})
    assert response.status_code == 400
    assert response.json()['error'] == 'token is missing'


@gitlab_api.use()
def test_register_invalid_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/runners/', {'token': 'an_invalid_token'})
    assert response.status_code == 403
    assert response.json()['message'] == '403 Forbidden'


@gitlab_api.use()
def test_register_valid(gitlab_api):
    response = requests.post(API_ENDPOINT+'/runners/', {'token': gitlab_api.token})
    # Check the response
    assert response.status_code == 200, response.json()
    data = response.json()
    assert 'id' in data
    assert 'token' in data
    # Check the API's internal state
    assert len(gitlab_api.runners) == 1
    assert data['token'] in gitlab_api.runners


@gitlab_api.use(n_runners=2)
def test_verify_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/runners/verify', {})
    assert response.status_code == 400
    assert response.json()['error'] == 'token is missing'


@gitlab_api.use(n_runners=2)
def test_verify_invalid_token(gitlab_api):
    response = requests.post(API_ENDPOINT+'/runners/verify', {'token': 'an_invalid_token'})
    assert response.status_code == 403
    assert response.json()['message'] == '403 Forbidden'


@gitlab_api.use(n_runners=2)
def test_verify_valid(gitlab_api):
    runner_token = list(gitlab_api.runners.keys())[0]

    response = requests.post(API_ENDPOINT+'/runners/verify', {'token': runner_token})
    # Check the response
    assert response.status_code == 200, response.json()
    assert response.json() == 200
    # Check the API's internal state
    assert len(gitlab_api.runners) == 2
