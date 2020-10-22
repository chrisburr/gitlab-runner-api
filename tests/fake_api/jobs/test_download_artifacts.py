from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gitlab_runner_api.testing import API_ENDPOINT, FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4, n_success=1, n_with_artifacts=1)
def test_valid_body(gitlab_api):
    job = gitlab_api.completed_jobs[0]

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts", data={"token": job.token}
    )
    # Check the response
    assert response.status_code == 200
    assert response.content == job.file_data

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts", params={"token": job.token}
    )
    # Check the response
    assert response.status_code == 200
    assert response.content == job.file_data

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
        headers={"JOB-TOKEN": job.token},
    )
    # Check the response
    assert response.status_code == 200
    assert response.content == job.file_data

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 1


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4, n_success=1, n_with_artifacts=1)
def test_auth_error(gitlab_api):
    job = gitlab_api.completed_jobs[0]

    headers = {"JOB-TOKEN": job.token}
    params = {"token": job.token}

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
        data={"token": "invalid_token"},
        params=params,
        headers=headers,
    )
    # Check the response
    assert response.status_code == 403
    assert response.json() == {"message": "403 Forbidden"}

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
        params={"token": "invalid_token"},
        headers=headers,
    )
    # Check the response
    assert response.status_code == 403
    assert response.json() == {"message": "403 Forbidden"}

    response = requests.get(
        API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
        headers={"JOB-TOKEN": "invalid_token"},
    )
    # Check the response
    assert response.status_code == 403
    assert response.json() == {"message": "403 Forbidden"}

    response = requests.get(API_ENDPOINT + "/jobs/" + job.id + "/artifacts")
    # Check the response
    assert response.status_code == 403
    assert response.json() == {"message": "403 Forbidden"}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 1
