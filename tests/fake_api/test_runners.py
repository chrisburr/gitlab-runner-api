from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest
import requests

from gitlab_runner_api.testing import FakeGitlabAPI, API_ENDPOINT


gitlab_api = FakeGitlabAPI()


@gitlab_api.use()
def test_register_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT + "/runners/", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "token is missing"


@gitlab_api.use()
def test_register_invalid_token(gitlab_api):
    response = requests.post(
        API_ENDPOINT + "/runners/", json={"token": "an_invalid_token"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "403 Forbidden"


@gitlab_api.use()
def test_register_valid(gitlab_api):
    data = {
        "token": gitlab_api.token,
        "description": "A description",
        "info": {
            "name": "a name",
            "version": "a version",
            "revision": "a revision",
            "platform": "a platform",
            "architecture": "a architecture",
            "executor": "a executor",
            # TODO 'features': {},
        },
        "active": True,
        "locked": False,
        "run_untagged": True,
        "tag_list": "cvmfs,dirac",
        "maximum_timeout": 5 * 60 * 60,
    }
    response = requests.post(API_ENDPOINT + "/runners/", json=data)
    # Check the response
    assert response.status_code == 201, response.json()
    data = response.json()
    assert "id" in data
    assert "token" in data
    # Check the API's internal state
    assert len(gitlab_api.runners) == 1
    runner = gitlab_api.runners[data["token"]]
    assert runner.description == "A description"
    assert runner.name == "a name"
    assert runner.version == "a version"
    assert runner.revision == "a revision"
    assert runner.platform == "a platform"
    assert runner.architecture == "a architecture"
    assert runner.executor == "a executor"
    assert runner.active is True
    assert runner.locked is False
    assert runner.run_untagged is True
    assert runner.tag_list == ["cvmfs", "dirac"]
    assert runner.maximum_timeout == 5 * 60 * 60


@gitlab_api.use(n_runners=2)
def test_invalid_data(gitlab_api):
    # Top level parameters
    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "description": ["bad\n", "value"]},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "description is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/", json={"token": gitlab_api.token, "active": "True"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "active is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/", json={"token": gitlab_api.token, "locked": "False"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "locked is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "run_untagged": "True"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "run_untagged is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "tag_list": ["cvmfs", "dirac"]},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "tag_list is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "maximum_timeout": "500"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "maximum_timeout is invalid"

    # Parameters in the info dictionary
    response = requests.post(
        API_ENDPOINT + "/runners/", json={"token": gitlab_api.token, "info": []}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "info is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"name": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "name is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"version": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "version is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"revision": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "revision is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"platform": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "platform is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"architecture": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "architecture is invalid"

    response = requests.post(
        API_ENDPOINT + "/runners/",
        json={"token": gitlab_api.token, "info": {"executor": True}},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "executor is invalid"

    # Parameters in the features dictionary
    with pytest.raises(NotImplementedError):
        response = requests.post(
            API_ENDPOINT + "/runners/",
            json={"token": gitlab_api.token, "info": {"features": {}}},
        )


@gitlab_api.use(n_runners=2)
def test_verify_no_token(gitlab_api):
    response = requests.post(API_ENDPOINT + "/runners/verify", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "token is missing"


@gitlab_api.use(n_runners=2)
def test_verify_invalid_token(gitlab_api):
    response = requests.post(
        API_ENDPOINT + "/runners/verify", json={"token": "an_invalid_token"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "403 Forbidden"


@gitlab_api.use(n_runners=2)
def test_verify_valid(gitlab_api):
    runner_token = list(gitlab_api.runners.keys())[0]

    response = requests.post(
        API_ENDPOINT + "/runners/verify", json={"token": runner_token}
    )
    # Check the response
    assert response.status_code == 200, response.json()
    assert response.json() == 200
    # Check the API's internal state
    assert len(gitlab_api.runners) == 2
