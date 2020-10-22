from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest
import requests

from gitlab_runner_api.testing import (
    API_ENDPOINT,
    FakeGitlabAPI,
    run_test_with_artifact,
)


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
@run_test_with_artifact
def test_valid(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.running_jobs[1]

    with open(artifact_fn, "rb") as fp:
        headers = {"JOB-TOKEN": job.token}
        data = {}
        files = {"file": ("artifacts.zip", fp)}
        response = requests.post(
            API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
            data,
            headers=headers,
            files=files,
        )

    # Check the response
    assert response.status_code == 201
    # TODO: Validate schema
    assert response.json() == job.as_dict()
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        if j == job:
            assert j.artifact_sha_hash == artifact_hash
            # TODO Check lifetime
        else:
            assert j.artifact_sha_hash is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
@run_test_with_artifact
def test_valid_custom_expiry(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.running_jobs[1]

    with open(artifact_fn, "rb") as fp:
        headers = {"JOB-TOKEN": job.token}
        data = {"expire_in": "1 hour"}
        files = {"file": ("artifacts.zip", fp)}
        response = requests.post(
            API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
            data,
            headers=headers,
            files=files,
        )

    # Check the response
    assert response.status_code == 201
    # TODO: Validate schema
    assert response.json() == job.as_dict()
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        if j == job:
            assert j.artifact_sha_hash == artifact_hash
            # TODO Check lifetime
        else:
            assert j.artifact_sha_hash is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
@run_test_with_artifact
def test_set_type_and_format(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.running_jobs[1]

    with pytest.raises(NotImplementedError):
        with open(artifact_fn, "rb") as fp:
            headers = {"JOB-TOKEN": job.token}
            data = {"artifact_type": "1 hour"}
            files = {"file": ("artifacts.zip", fp)}
            requests.post(
                API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
                data,
                headers=headers,
                files=files,
            )

    with pytest.raises(NotImplementedError):
        with open(artifact_fn, "rb") as fp:
            headers = {"JOB-TOKEN": job.token}
            data = {"artifact_format": "1 hour"}
            files = {"file": ("artifacts.zip", fp)}
            requests.post(
                API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
                data,
                headers=headers,
                files=files,
            )

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        assert j.artifact_sha_hash is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
@run_test_with_artifact
def test_auth_error(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.running_jobs[1]

    headers_to_try = {
        "Wrong token": {"JOB-TOKEN": "invalid_token"},
        "No token or content range": {},
    }
    for name, headers in headers_to_try.items():
        with open(artifact_fn, "rb") as fp:
            data = {"artifact_format": "1 hour"}
            files = {"file": ("artifacts.zip", fp)}
            response = requests.post(
                API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
                data,
                headers=headers,
                files=files,
            )
        # Check the response
        assert response.status_code == 403, name
        assert response.json() == {"message": "403 Forbidden"}, name

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        assert j.artifact_sha_hash is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=2, n_success=4, n_failed=1)
@run_test_with_artifact
def test_completed(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.completed_jobs[1]

    with open(artifact_fn, "rb") as fp:
        headers = {"JOB-TOKEN": job.token}
        data = {}
        files = {"file": ("artifacts.zip", fp)}
        response = requests.post(
            API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
            data,
            headers=headers,
            files=files,
        )
    # Check the response
    assert response.status_code == 403, response.json()
    assert response.json() == {"message": "403 Forbidden  - Job is not running"}

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 5
    for j in gitlab_api.running_jobs + gitlab_api.completed_jobs:
        assert j.artifact_sha_hash is None


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
@run_test_with_artifact
def test_already_uploaded(gitlab_api, artifact_fn, artifact_hash):
    job = gitlab_api.running_jobs[1]

    with open(artifact_fn, "rb") as fp:
        headers = {"JOB-TOKEN": job.token}
        data = {}
        files = {"file": ("artifacts.zip", fp)}
        response = requests.post(
            API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
            data,
            headers=headers,
            files=files,
        )
    assert response.status_code == 201

    with open(artifact_fn, "rb") as fp:
        headers = {"JOB-TOKEN": job.token}
        data = {}
        files = {"file": ("artifacts.zip", fp)}
        response = requests.post(
            API_ENDPOINT + "/jobs/" + job.id + "/artifacts",
            data,
            headers=headers,
            files=files,
        )
    # Check the response
    assert response.status_code == 400
    assert response.json() == {
        "message": '400 (Bad request) "Already uploaded" not given'
    }
    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 4
    assert len(gitlab_api.completed_jobs) == 0
    for j in gitlab_api.running_jobs:
        if j == job:
            assert j.artifact_sha_hash == artifact_hash
        else:
            assert j.artifact_sha_hash is None
