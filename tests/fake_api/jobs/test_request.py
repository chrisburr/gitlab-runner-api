from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gitlab_runner_api.testing import API_ENDPOINT, FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2)
def test_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT + "/jobs/request", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "token is missing"


@gitlab_api.use(n_runners=2)
def test_invalid_token(gitlab_api):
    response = requests.post(
        API_ENDPOINT + "/jobs/request", json={"token": "an_invalid_token"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "403 Forbidden"


@gitlab_api.use(n_runners=2)
def test_none_available(gitlab_api):
    runner_token = list(gitlab_api.runners.keys())[0]
    response = requests.post(
        API_ENDPOINT + "/jobs/request", json={"token": runner_token}
    )
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
    data = {"token": runner_token, "info": {"description": "new description"}}
    response = requests.post(API_ENDPOINT + "/jobs/request", json=data)

    # Check the response
    assert response.status_code == 201
    # TODO: Validate schema
    assert response.json()["job_info"]["name"] == expected_job["name"]
    assert gitlab_api._runners[runner_token].description == "new description"

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 2
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_runners=2, n_pending=3)
def test_bad_info(gitlab_api):
    runner_token = list(gitlab_api.runners.keys())[0]
    data = {"token": runner_token, "info": []}
    response = requests.post(API_ENDPOINT + "/jobs/request", json=data)

    # Check the response
    assert response.status_code == 400
    assert response.json() == {"error": "info is invalid"}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 0
    assert len(gitlab_api.completed_jobs) == 0
