from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from copy import deepcopy
import json
import pytest
import tempfile

import gitlab_runner_api
from gitlab_runner_api import (
    AlreadyFinishedExcpetion,
    AuthException,
    Job,
    Runner,
    failure_reasons,
)
from gitlab_runner_api.testing import FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_pending=2)
def test_request_job(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    assert isinstance(runner.request_job(), Job)
    assert isinstance(runner.request_job(), Job)
    assert runner.request_job() is None

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 0
    assert len(gitlab_api.running_jobs) == 2
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_request_job_invalid_token(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    runner.request_job()
    runner._token = "invalid_token"
    with pytest.raises(AuthException):
        runner.request_job()

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_repr(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    print(repr(job))
    assert str(job.id) in repr(job)
    assert str(job.token) in repr(job)
    assert str(job.state) in repr(job)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_serialise(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    as_string = job.dumps()
    job_from_string = Job.loads(as_string)
    assert job == job_from_string

    with tempfile.NamedTemporaryFile() as fp:
        job.dump(fp.name)
        job_from_file = Job.load(fp.name)
    assert job == job_from_file

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_serialise_invalid_version(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    serialised_job = json.loads(job.dumps())
    serialised_job[0] = 2
    as_string = json.dumps(serialised_job)

    with pytest.raises(ValueError):
        Job.loads(as_string)

    with tempfile.NamedTemporaryFile(mode="wt") as fp:
        json.dump(as_string, fp)
        fp.flush()
        with pytest.raises(ValueError):
            Job.load(fp.name)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


def check_finished(n_pending, n_running, n_completed, status, log, failure_reason):
    assert len(gitlab_api.pending_jobs) == n_pending
    assert len(gitlab_api.running_jobs) == n_running
    assert len(gitlab_api.completed_jobs) == n_completed

    assert gitlab_api.completed_jobs[0].status == status
    log_prefix = (
        "Running with gitlab_runner_api " + gitlab_runner_api.__version__ + "\n"
    )
    assert gitlab_api.completed_jobs[0].log == log_prefix + log
    assert gitlab_api.completed_jobs[0].failure_reason == failure_reason


@gitlab_api.use(n_pending=2)
def test_bad_job_info(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job_info = deepcopy(job._job_info)
    del job_info["variables"]
    with pytest.raises(KeyError):
        Job(runner, job_info, fail_on_error=False)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_bad_job_info_and_fail(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job_info = deepcopy(job._job_info)
    del job_info["variables"]
    with pytest.raises(KeyError):
        Job(runner, job_info)

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 0
    assert len(gitlab_api.completed_jobs) == 1

    assert gitlab_api.completed_jobs[0].status == "failed"
    assert "KeyError" in gitlab_api.completed_jobs[0].log
    assert gitlab_api.completed_jobs[0].failure_reason == "runner_system_failure"


# Test setting job status as success
@gitlab_api.use(n_pending=2)
def test_set_success(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job.set_success()

    # Check the API's internal state
    check_finished(1, 0, 1, "success", "", None)


@gitlab_api.use(n_pending=2)
def test_set_success_bad_auth(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job._token = "invalid_token"
    with pytest.raises(AuthException):
        job.set_success()

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_set_success_twice(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job.set_success()

    with pytest.raises(AlreadyFinishedExcpetion):
        job.set_success()

    # Check the API's internal state
    check_finished(1, 0, 1, "success", "", None)


@gitlab_api.use(n_pending=2)
def test_set_success_with_log(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    job.log += "test log text"
    job.set_success()

    # Check the API's internal state
    check_finished(1, 0, 1, "success", "test log text", None)


@gitlab_api.use(n_pending=2)
def test_bad_log(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    with pytest.raises(TypeError):
        job.log += 3456789

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@pytest.mark.xfail(raises=NotImplementedError)
@gitlab_api.use(n_pending=2)
def test_set_success_with_artifacts(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    job.set_success(artifacts=[])


# Test setting job status as failed
@gitlab_api.use(n_pending=2)
def test_set_failed(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job.set_failed()

    # Check the API's internal state
    check_finished(1, 0, 1, "failed", "", "unknown_failure")


@gitlab_api.use(n_pending=2)
def test_set_failed_bad_auth(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job._token = "invalid_token"
    with pytest.raises(AuthException):
        job.set_failed()

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 1
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 0


@gitlab_api.use(n_pending=2)
def test_set_failed_twice(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()

    job.set_failed()

    with pytest.raises(AlreadyFinishedExcpetion):
        job.set_failed()

    # Check the API's internal state
    check_finished(1, 0, 1, "failed", "", "unknown_failure")


@gitlab_api.use(n_pending=2)
def test_set_failed_with_log(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    job.log += "test log text"
    job.set_failed()

    # Check the API's internal state
    check_finished(1, 0, 1, "failed", "test log text", "unknown_failure")


@pytest.mark.xfail(raises=NotImplementedError)
@gitlab_api.use(n_pending=2)
def test_set_failed_with_artifacts(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)
    job = runner.request_job()
    job.set_failed(artifacts=[])


@gitlab_api.use(n_pending=10)
def test_set_failed_reason(gitlab_api):
    runner = Runner.register("https://gitlab.cern.ch", gitlab_api.token)

    job = runner.request_job()
    with pytest.raises(ValueError):
        job.set_failed(failure_reason="unknown_failure")

    job = runner.request_job()
    job.set_failed(failure_reasons.ApiFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "api_failure"

    job = runner.request_job()
    job.set_failed(failure_reasons.MissingDependencyFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "missing_dependency_failure"

    job = runner.request_job()
    job.set_failed(failure_reasons.RunnerSystemFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "runner_system_failure"

    job = runner.request_job()
    job.set_failed(failure_reasons.ScriptFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "script_failure"

    job = runner.request_job()
    job.set_failed(failure_reasons.StuckOrTimeoutFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "stuck_or_timeout_failure"

    job = runner.request_job()
    job.set_failed(failure_reasons.UnknownFailure())
    gitlab_api.completed_jobs[-1].failure_reason == "unknown_failure"

    # Check the API's internal state
    assert len(gitlab_api.pending_jobs) == 3
    assert len(gitlab_api.running_jobs) == 1
    assert len(gitlab_api.completed_jobs) == 6
