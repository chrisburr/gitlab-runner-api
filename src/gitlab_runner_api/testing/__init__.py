from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import inspect
import json
import string

import responses
import six

from .job import Job
from .runner import Runner
from .utils import (
    check_token,
    random_string,
    run_test_with_artifact,
    validate_runner_info,
)

API_ENDPOINT = "https://gitlab.cern.ch/api/v4"

__all__ = ["API_ENDPOINT", "FakeGitlabAPI", "test_log", "run_test_with_artifact"]

if six.PY2:
    getfullargspec = inspect.getargspec
else:
    getfullargspec = inspect.getfullargspec


class FakeGitlabAPI(object):
    def __init__(
        self,
        n_runners=0,
        n_pending=0,
        n_running=0,
        n_success=0,
        n_failed=0,
        n_with_artifacts=0,
    ):
        self.n_runners = n_runners
        self.n_pending = n_pending
        self.n_running = n_running
        self.n_success = n_success
        self.n_failed = n_failed
        self.n_with_artifacts = n_with_artifacts

        self._next_runner_id = 0
        self._next_job_id = 0

        self.do_init()

    def do_init(self):
        self._token = random_string(string.ascii_letters + "_-", 20)

        self._runners = {}

        self._jobs = []

    @property
    def token(self):
        return self._token

    @property
    def runners(self):
        return self._runners

    @property
    def pending_jobs(self):
        return [j for j in self._jobs if isinstance(j, dict)]

    @property
    def running_jobs(self):
        return [
            j for j in self._jobs if not isinstance(j, dict) and j.status == "running"
        ]

    @property
    def completed_jobs(self):
        return [
            j for j in self._jobs if not isinstance(j, dict) and j.status != "running"
        ]

    @property
    def next_runner_id(self):
        self._next_runner_id += 1
        return str(self._next_runner_id - 1)

    @property
    def next_job_id(self):
        self._next_job_id += 1
        return str(self._next_job_id - 1)

    def __enter__(self):
        self.do_init()
        self._rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
        self._rsps.__enter__()

        # Register callbacks
        self._rsps.add_callback(
            responses.POST,
            API_ENDPOINT + "/runners/",
            callback=self._register_runner_callback,
        )
        self._rsps.add_callback(
            responses.POST,
            API_ENDPOINT + "/runners/verify",
            callback=self._verify_runner_callback,
        )
        self._rsps.add_callback(
            responses.POST,
            API_ENDPOINT + "/jobs/request",
            callback=self._request_job_callback,
        )

        # Add fake data to the API
        for i in range(self.n_runners):
            _, runner = self.register_runner()

        for i in range(self.n_pending):
            self._jobs.append({"name": "MyJob" + str(i)})

        for i in range(self.n_running):
            assert self.n_runners > 0
            Job(self.next_job_id, {"name": "MyRunningJob" + str(i)}, self, runner)

        for i in range(self.n_success):
            assert self.n_runners > 0
            Job(self.next_job_id, {"name": "MyGoodJob" + str(i)}, self, runner)
            self.running_jobs[-1].status = "success"

        for i in range(self.n_failed):
            assert self.n_runners > 0
            Job(self.next_job_id, {"name": "MyBadJob" + str(i)}, self, runner)
            self.running_jobs[-1].status = "failed"

        if self.n_with_artifacts > self.n_success + self.n_failed:
            raise ValueError(
                "n_with_artifacts must be smaller than n_success + n_failed"
            )
        for i in range(self.n_with_artifacts):
            self.completed_jobs[i].upload_artifacts("archive.zip", b"some_data")

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self._rsps.__exit__(exception_type, exception_value, traceback)
        del self._rsps

    def use(
        self,
        n_runners=0,
        n_pending=0,
        n_running=0,
        n_success=0,
        n_failed=0,
        n_with_artifacts=0,
    ):
        def decorator(func):
            """Decorator to active the mocking for this API"""

            def new_func(caplog, *args, **kwargs):
                self.n_runners = n_runners
                self.n_pending = n_pending
                self.n_running = n_running
                self.n_success = n_success
                self.n_failed = n_failed
                self.n_with_artifacts = n_with_artifacts

                with self:
                    if "caplog" in getfullargspec(func).args:
                        result = func(*args, caplog=caplog, gitlab_api=self, **kwargs)
                    else:
                        result = func(*args, gitlab_api=self, **kwargs)
                return result

            return new_func

        return decorator

    def register_runner(self, **kwargs):
        token = random_string(string.hexdigits, 30)
        runner = Runner(self.next_runner_id, **kwargs)
        self._runners[token] = runner
        return token, runner

    def _register_runner_callback(self, request):
        payload, response = check_token(request, self.token)
        if response is not None:
            return response

        # Expand the nested dictionaries
        kwargs = payload.copy()
        if "token" in payload:
            del kwargs["token"]
        if "info" in payload:
            response = validate_runner_info(payload["info"])
            if not isinstance(response, dict):
                return response
            del kwargs["info"]
            kwargs.update(response)

        # Validate individual items
        if "tag_list" in kwargs:
            if not isinstance(kwargs["tag_list"], six.string_types):
                return (400, {}, json.dumps({"error": "tag_list is invalid"}))
            kwargs["tag_list"] = kwargs["tag_list"].split(",")
        expected_types = {
            "description": six.string_types,
            "active": bool,
            "locked": bool,
            "run_untagged": bool,
            "maximum_timeout": int,
        }
        for name, expected_type in expected_types.items():
            if name in kwargs:
                if not isinstance(kwargs[name], expected_type):
                    return (400, {}, json.dumps({"error": name + " is invalid"}))

        token, runner = self.register_runner(**kwargs)

        headers = {}
        response = {"id": runner.id, "token": token}
        return (201, headers, json.dumps(response))

    def _verify_runner_callback(self, request):
        payload, response = check_token(request, list(self._runners.keys()))
        if response is not None:
            return response

        headers = {}
        response = 200
        return (200, headers, json.dumps(response))

    def _request_job_callback(self, request):
        payload, response = check_token(request, list(self._runners.keys()))
        if response is not None:
            return response
        runner = self._runners[payload["token"]]

        if "info" in payload:
            response = validate_runner_info(payload["info"])
            if not isinstance(response, dict):
                return response
            runner.update(**response)

        if len(self.pending_jobs) == 0:
            return (204, {}, json.dumps({}))

        job = Job(self.next_job_id, self.pending_jobs.pop(0), self, runner)

        headers = {}
        response = job.as_dict()
        return (201, headers, json.dumps(response))


test_log = "\n".join([random_string(string.printable, 100) for i in range(10000)])
