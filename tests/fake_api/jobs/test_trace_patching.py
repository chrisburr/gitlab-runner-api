from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import requests

from gitlab_runner_api.testing import API_ENDPOINT, FakeGitlabAPI, test_log


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2, n_pending=3, n_running=2, n_success=4, n_failed=1)
def test(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]

    # Initial log update
    headers = {
        "JOB-TOKEN": expected_job.token,
        "Content-Range": "0-" + str(len(test_log[:1000])),
    }
    response = requests.patch(
        API_ENDPOINT + "/jobs/" + expected_job.id + "/trace",
        test_log[:1000],
        headers=headers,
    )
    # Check the response
    assert response.status_code == 202
    assert response.content.decode() == "0-" + str(len(test_log[:1000]))
    # Check the API's internal state
    assert gitlab_api.running_jobs[1].log == test_log[:1000]

    # Later log update
    headers = {
        "JOB-TOKEN": expected_job.token,
        "Content-Range": "1000-" + str(len(test_log[1000:1300])),
    }
    response = requests.patch(
        API_ENDPOINT + "/jobs/" + expected_job.id + "/trace",
        test_log[1000:1300],
        headers=headers,
    )
    # Check the response
    assert response.status_code == 202
    assert response.content.decode() == "0-1300"
    # Check the API's internal state
    assert gitlab_api.running_jobs[1].log == test_log[:1300]

    # And a final log update
    headers = {
        "JOB-TOKEN": expected_job.token,
        "Content-Range": "1300-" + str(len(test_log[1300:])),
    }
    response = requests.patch(
        API_ENDPOINT + "/jobs/" + expected_job.id + "/trace",
        test_log[1300:],
        headers=headers,
    )
    # Check the response
    assert response.status_code == 202
    assert response.content.decode() == "0-" + str(len(test_log))
    # Check the API's internal state
    assert gitlab_api.running_jobs[1].log == test_log

    # Check the API's internal state for the number of jobs
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 5
    for job in gitlab_api.running_jobs + gitlab_api.completed_jobs:
        if job == gitlab_api.running_jobs[1]:
            assert job.log == test_log
        else:
            assert job.log == ""


@gitlab_api.use(n_runners=2, n_pending=3, n_running=2, n_success=4, n_failed=1)
def test_auth_error(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]

    headers_to_try = {
        "No token": {"Content-Range": "0-" + str(len(test_log))},
        "Wrong token": {
            "JOB-TOKEN": "invalid_token",
            "Content-Range": "0-" + str(len(test_log)),
        },
        "No token or content range": {},
        "Wrong token without content range": {"JOB-TOKEN": "invalid_token"},
    }
    for name, headers in headers_to_try.items():
        response = requests.patch(
            API_ENDPOINT + "/jobs/" + expected_job.id + "/trace",
            test_log,
            headers=headers,
        )
        # Check the response
        assert response.status_code == 403, name
        assert response.json() == {"message": "403 Forbidden"}, name

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 5
    for job in gitlab_api.running_jobs + gitlab_api.completed_jobs:
        assert job.log == ""


@gitlab_api.use(n_runners=2, n_pending=3, n_running=2, n_success=4, n_failed=1)
def test_range_error(gitlab_api):
    expected_job = gitlab_api.running_jobs[1]

    headers = {"JOB-TOKEN": expected_job.token}
    response = requests.patch(
        API_ENDPOINT + "/jobs/" + expected_job.id + "/trace", test_log, headers=headers
    )
    # Check the response
    assert response.status_code == 400
    assert response.json() == {"error": "Missing header Content-Range"}
    assert response.headers["Range"] == "0-0"

    headers_to_try = {
        "1 Wrong start": {
            "JOB-TOKEN": expected_job.token,
            "Content-Range": "5-" + str(len(test_log)),
        },
        "2 Wrong length": {
            "JOB-TOKEN": expected_job.token,
            "Content-Range": "0-" + str(len(test_log) - 100),
        },
        "3 Badly formatted": {
            "JOB-TOKEN": expected_job.token,
            "Content-Range": "0-" + str(len(test_log)) + "-10",
        },
        "4 Not a number": {"JOB-TOKEN": expected_job.token, "Content-Range": "0-b"},
    }
    for name, headers in sorted(headers_to_try.items()):
        response = requests.patch(
            API_ENDPOINT + "/jobs/" + expected_job.id + "/trace",
            test_log,
            headers=headers,
        )
        # Check the response
        assert response.status_code == 416, name
        assert response.json() == {"error": "Range Not Satisfiable"}, name
        assert response.headers["Range"] == "0-0"

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 5
    for job in gitlab_api.running_jobs + gitlab_api.completed_jobs:
        assert job.log == ""


@gitlab_api.use(n_runners=2, n_pending=3, n_running=2, n_success=4, n_failed=1)
def test_completed(gitlab_api):
    expected_job = gitlab_api.completed_jobs[1]

    headers = {
        "JOB-TOKEN": expected_job.token,
        "Content-Range": "0-" + str(len(test_log)),
    }
    response = requests.patch(
        API_ENDPOINT + "/jobs/" + expected_job.id + "/trace", test_log, headers=headers
    )
    # Check the response
    assert response.status_code == 403, response.json()
    assert response.json() == {"message": "403 Forbidden  - Job is not running"}
    assert "Range" not in response.headers
