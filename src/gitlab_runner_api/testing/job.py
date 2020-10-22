from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import hashlib
import json
import re
import string

from requests_toolbelt.multipart import decoder
import responses

from .utils import check_token, random_string, validate_runner_info

API_ENDPOINT = "https://gitlab.cern.ch/api/v4"

__all__ = [
    "Job",
]


class JobVariable:
    def __init__(self, key, value, public=True):
        self.key = key
        self.public = public
        self.value = value

    def as_dict(self):
        return {
            "key": self.key,
            "public": self.public,
            "value": self.value,
        }


class Job(object):
    valid_failure_reasons = [
        "unknown_failure",
        "script_failure",
        "api_failure",
        "stuck_or_timeout_failure",
        "runner_system_failure",
        "missing_dependency_failure",
    ]

    def __init__(self, job_id, job_info, api, runner):
        self._id = job_id
        self._job_info = job_info
        self._token = random_string(string.ascii_letters + "_-", 20)
        self._variables = [
            JobVariable("GITLAB_CI", "true"),
            JobVariable("GITLAB_USER_EMAIL", "someone@example.com"),
            JobVariable("GITLAB_USER_LOGIN", "someone"),
            JobVariable("CI_PROJECT_PATH", "someone/some-project"),
            JobVariable(
                "CI_JOB_URL", "https://gitlab.com/someone/some-project/-/jobs/1234"
            ),
            JobVariable(
                "CI_REPOSITORY_URL",
                "https://gitlab.cern.ch/lhcb-gitlab-runners/runner-api.git",
            ),
            JobVariable("CI_COMMIT_SHA", "ff37e0611e570eeb4f0f9c704abd698a40759ba6"),
            JobVariable("CI_COMMIT_REF_NAME", "master"),
            JobVariable("CI_JOB_NAME", "example_job"),
            JobVariable("CI_JOB_ID", "1234567"),
        ]
        self.log = ""
        self._status = "running"
        self._failure_reason = None
        self._file_data = None
        self._api = api
        self._runner = runner

        if job_info in self._api._jobs:
            self._api._jobs.pop(self._api._jobs.index(job_info))
        self._api._jobs.append(self)

        # Resister additional callbacks
        # Update a job's status
        self._api._rsps.add_callback(
            responses.PUT,
            API_ENDPOINT + "/jobs/" + self.id,
            callback=self._update_job_callback,
        )
        # Append to the job's log
        self._api._rsps.add_callback(
            responses.PATCH,
            API_ENDPOINT + "/jobs/" + self.id + "/trace",
            callback=self._update_log_callback,
        )
        # Upload job artefacts
        self._api._rsps.add_callback(
            responses.POST,
            API_ENDPOINT + "/jobs/" + self.id + "/artifacts",
            callback=self._upload_artifacts_callback,
        )

    def __repr__(self):
        return "gitlab_runner_api.testing.Job(id={id}, status={status})".format(
            id=self.id, status=self.status
        )

    @property
    def id(self):
        return self._id

    @property
    def job_info(self):
        return self._job_info

    @property
    def token(self):
        return self._token

    @property
    def status(self):
        return self._status

    @property
    def file_data(self):
        return self._file_data

    @property
    def artifact_sha_hash(self):
        if self.file_data is None:
            return None
        hasher = hashlib.sha256()
        hasher.update(self.file_data)
        return hasher.hexdigest()

    @status.setter
    def status(self, new_status):
        started_statuses = ["running", "success", "failed", "skipped", "manual"]
        active_statuses = ["pending", "running"]
        completed_statuses = ["success", "failed", "canceled", "skipped"]
        ordered_statuses = [
            "failed",
            "pending",
            "running",
            "manual",
            "canceled",
            "success",
            "skipped",
            "created",
        ]

        assert new_status in ordered_statuses, new_status
        self._status = new_status

    @property
    def failure_reason(self):
        return self._failure_reason

    @failure_reason.setter
    def failure_reason(self, new_failure_reason):
        if self.status != "failed":
            raise ValueError(
                "Cannot set failure reason on a job with status: " + self.status
            )
        assert new_failure_reason in self.valid_failure_reasons
        self._failure_reason = new_failure_reason

    def _update_job_callback(self, request):
        payload = json.loads(request.body)
        if (
            "failure_reason" in payload
            and payload["failure_reason"] not in self.valid_failure_reasons
        ):
            return (
                400,
                {},
                json.dumps({"error": "failure_reason does not have a valid value"}),
            )

        if "info" in payload:
            response = validate_runner_info(payload["info"])
            if not isinstance(response, dict):
                return response
            self._runner.update(**response)

        payload, response = check_token(request, self.token)
        if response is not None:
            return response

        if self.status != "running":
            return (
                403,
                {},
                json.dumps({"message": "403 Forbidden  - Job is not running"}),
            )

        if "trace" in payload:
            self.log = payload["trace"]

        if "state" in payload:
            if payload["state"] in ["success", "failed"]:
                self.status = payload["state"]
                if "failure_reason" in payload and payload["state"] == "failed":
                    self.failure_reason = payload["failure_reason"]
                return (200, {}, json.dumps(True))
            else:
                print(
                    "API ignores this but an invalid job state was received:",
                    payload["state"],
                )

        return (200, {}, json.dumps(None))

    def _update_log_callback(self, request):
        if (
            "JOB-TOKEN" not in request.headers
            or request.headers["JOB-TOKEN"] != self.token
        ):
            return (403, {}, json.dumps({"message": "403 Forbidden"}))

        if self.status != "running":
            return (
                403,
                {},
                json.dumps({"message": "403 Forbidden  - Job is not running"}),
            )

        headers = {"Range": "0-" + str(len(self.log))}

        if "Content-Range" not in request.headers:
            return (400, headers, json.dumps({"error": "Missing header Content-Range"}))
        content_range = request.headers["Content-Range"].split("-")

        try:
            if len(content_range) != 2:
                raise ValueError()
            content_start = int(content_range[0])
            content_length = int(content_range[1])
            if content_start != len(self.log):
                raise ValueError()
            if content_length != len(request.body):
                raise ValueError()
        except ValueError:
            return (416, headers, json.dumps({"error": "Range Not Satisfiable"}))

        self.log += request.body

        headers["Range"] = "0-" + str(len(self.log))
        headers["Job-Status"] = self.status

        return (202, headers, headers["Range"])

    def upload_artifacts(self, filename, data):
        self._filename = filename
        self._file_data = data

        # Register callback for downloading
        self._api._rsps.add_callback(
            responses.GET,
            API_ENDPOINT + "/jobs/" + self.id + "/artifacts",
            callback=self._download_artifacts_callback,
        )

    def _upload_artifacts_callback(self, request):
        # TODO We should authorise the artifacts first

        if (
            "JOB-TOKEN" not in request.headers
            or request.headers["JOB-TOKEN"] != self.token
        ):
            return (403, {}, json.dumps({"message": "403 Forbidden"}))

        if self.status != "running":
            return (
                403,
                {},
                json.dumps({"message": "403 Forbidden  - Job is not running"}),
            )

        if self.file_data is not None:
            return (
                400,
                {},
                json.dumps(
                    {"message": '400 (Bad request) "Already uploaded" not given'}
                ),
            )

        payload = {}
        for part in decoder.MultipartDecoder(
            request.body, request.headers["Content-Type"]
        ).parts:
            header = (
                part.headers[b"Content-Disposition"].decode(part.encoding).split("; ")
            )
            assert header[0] == "form-data"
            header = {h.split("=")[0]: h.split("=")[1][1:-1] for h in header[1:]}

            assert header["name"] not in payload
            if header["name"] == "file":
                assert len(header) == 2
                payload[header["name"]] = (header["filename"], part.content)
            else:
                assert len(header) == 1
                payload[header["name"]] = part.text
        file_name, file_data = payload["file"]

        if "artifact_type" in payload or "artifact_format" in payload:
            raise NotImplementedError("Not sure what this does")

        if "expire_in" in payload:
            pass

        # TODO I think this should update the job's underlying job_info object
        # https://gitlab.com/gitlab-org/gitlab-ce/blob/78b3eea7d248c6d3c48b615c9df24a95cb5fd1d8/lib/api/runner.rb#L292
        self.upload_artifacts(file_name, file_data)

        headers = {}
        response = self.as_dict()
        return (201, headers, json.dumps(response))

    def _download_artifacts_callback(self, request):
        if request.body:
            body_match = re.search(r"token=([A-Za-z0-9_-]+)&?", request.body)
        else:
            body_match = None
        token_match = re.search(r"token=([A-Za-z0-9_-]+)&?", request.path_url)
        if body_match:
            (recieved_token,) = body_match.groups()
        elif token_match:
            (recieved_token,) = token_match.groups()
        elif "JOB-TOKEN" in request.headers:
            recieved_token = request.headers["JOB-TOKEN"]
        else:
            recieved_token = None

        if recieved_token != self.token:
            return (403, {}, json.dumps({"message": "403 Forbidden"}))

        headers = {}
        return (200, headers, self.file_data)

    def as_dict(self):
        return {
            "allow_git_fetch": True,
            "artifacts": [
                # If there are no artefacts this should be: None
                {
                    "name": None,  # Name of the zip file uploaded to GitLab (may contain $VAR)
                    "untracked": None,  # If true add all untracked files are as artifacts
                    "paths": ["binaries/", ".config"],
                    "when": None,  # on_success, on_failure, always
                    "expire_in": None,
                }
            ],
            "cache": [None],
            "credentials": [
                {
                    "password": self.token,
                    "type": "registry",
                    "url": "gitlab-registry.cern.ch",
                    "username": "gitlab-ci-token",
                }
            ],
            "dependencies": [
                # {"id": some_job_id, "name": "some_job_name", "token": "some_job_token"},
                # {"id": some_job_id, "name": "some_job_name", "token": "some_job_token"},
            ],
            "features": {"trace_sections": True},
            "git_info": {
                "before_sha": "0000000000000000000000000000000000000000",
                "ref": "master",
                "ref_type": "branch",
                "repo_url": "https://gitlab.cern.ch/lhcb-gitlab-runners/runner-api.git",
                "sha": "ff37e0611e570eeb4f0f9c704abd698a40759ba6",
            },
            "id": int(self.id),
            "image": {
                "entrypoint": None,
                "name": "gitlab-registry.cern.ch/lhcb-docker/python-deployment:centos7",
            },
            "job_info": {
                "name": self.job_info["name"],
                "project_id": 40330,
                "project_name": "test-runner",
                "stage": "first_stage",
            },
            "runner_info": {"runner_session_url": None, "timeout": 3600},
            "services": [],
            "steps": [
                {
                    "allow_failure": False,
                    "name": "script",
                    "script": ["pwd", "ls", "env",],
                    "timeout": 3600,
                    "when": "on_success",
                }
            ],
            "token": self.token,
            "variables": [v.as_dict() for v in self._variables],
        }
