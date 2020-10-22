from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    "Job",
]

import json
import re
from traceback import format_exc

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

import requests

from .exceptions import AlreadyFinishedExcpetion, AuthException, JobCancelledException
from .failure_reasons import _FailureReason, RunnerSystemFailure, UnknownFailure
from .logging import logger
from .version import CURRENT_DATA_VERSION, package_version


class Job(object):
    @classmethod
    def load(cls, filename):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        filename : :obj:`str`
            Path to file that represents the job to initialise.

        Returns
        -------
        :py:class:`Job <gitlab_runner_api.Job>`
        """
        with open(filename, "rt") as fp:
            return cls.loads(fp.read())

    @classmethod
    def loads(cls, data):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        data : :obj:`str`
            String representing the job to initialise

        Returns
        -------
        :py:class:`Job <gitlab_runner_api.Job>`
        """
        data = json.loads(data)
        version, data = data[0], data[1:]
        if version == 1:
            from .runner import Runner

            runner_info, job_info, state, log = data
            return cls(
                Runner.loads(runner_info),
                job_info,
                fail_on_error=False,
                state=state,
                log=log,
            )
        else:
            raise ValueError("Unrecognised data version: " + str(version))

    def __init__(self, runner, job_info, fail_on_error=True, state="running", log=None):
        self._runner = runner
        self._state = "running"  # All jobs start as running
        self.state = state
        self._log = JobLog(self, log)
        # TODO Create and validate a schema for the job_info dict
        self._job_info = job_info
        try:
            self._parse_job_info()
        except Exception:
            exception_string = format_exc()
            logger.fatal(
                "%s: Failed to parse job %d's description\n%s",
                urlparse(self._runner.api_url).netloc,
                self.id,
                exception_string,
            )
            if fail_on_error:
                self.log += "gitlab_runner_api failed to parse job description\n"
                self.log += exception_string
                self.set_failed(RunnerSystemFailure())
            raise

    def _parse_job_info(self):
        self._id = self._job_info["id"]

        self._token = self._job_info["token"]

        self._variables = {}
        for var_info in self._job_info["variables"]:
            logger.debug(
                "%s: Parsing environment variable from job %d (%s)",
                urlparse(self._runner.api_url).netloc,
                self.id,
                repr(var_info),
            )
            var = EnvVar(**var_info)
            self._variables[var.key] = var

        internal_variables = [
            EnvVar("CI_PROJECT_DIR", "/builds/" + self.project_path, True),
            EnvVar("CI_SERVER", "yes", True),
            EnvVar("CI_DISPOSABLE_ENVIRONMENT", "true", True),
        ]
        for var in internal_variables:
            self._variables[var.key] = var

    def __repr__(self):
        return "Job(id={id}, token={token}, state={state})".format(
            id=self.id, token=self.token, state=self.state
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def dump(self, filename):
        """Serialise this job as a file which can be loaded with `Job.load`.

        Parameters
        ----------
        filename : :obj:`str`
            Registration token
        """
        with open(filename, "wt") as fp:
            fp.write(self.dumps())

    def dumps(self):
        """Serialise this job as a string which can be loaded with with `Job.loads`.

        Returns
        -------
        :obj:`str`
            String representation of the job that can be loaded with
            `Job.loads`
        """
        return json.dumps(
            [
                CURRENT_DATA_VERSION,
                self._runner.dumps(),
                self._job_info,
                self.state,
                str(self.log),
            ]
        )

    def auth(self):
        response = requests.put(
            self._runner.api_url + "/api/v4/jobs/" + str(self.id),
            json={"token": self.token},
        )
        if response.status_code == 200:
            pass
        elif response.status_code == 403:
            if response.headers["Job-Status"] == "canceled":
                raise JobCancelledException()
            else:
                raise AuthException()
        else:
            raise NotImplementedError(
                "Unrecognised status code from request", response, response.content
            )

    def set_success(self, artifacts=None):
        self._update_state("success", artifacts)

    def set_failed(self, failure_reason=None, artifacts=None):
        self._update_state("failed", artifacts, failure_reason)

    def _update_state(self, state=None, artifacts=None, failure_reason=None):
        if self.state != "running":
            raise AlreadyFinishedExcpetion(
                "Job {id} has already finished as {state}".format(
                    id=self.id, state=self.state
                )
            )

        data = {
            "token": self.token,
        }

        data["trace"] = str(self.log)

        if state is not None:
            data["state"] = state

        if state == "failed":
            if failure_reason is None:
                failure_reason = UnknownFailure()
            elif not isinstance(failure_reason, _FailureReason):
                raise ValueError()
            data["failure_reason"] = str(failure_reason)

        if artifacts is not None:
            self._upload_artifacts(artifacts)

        response = requests.put(
            self._runner.api_url + "/api/v4/jobs/" + str(self.id), json=data
        )

        if response.status_code == 200:
            if state is None:
                logger.info(
                    "%s: Updated log for job %d", urlparse(response.url).netloc, self.id
                )
            else:
                logger.info(
                    "%s: Set job %d as %s",
                    urlparse(response.url).netloc,
                    self.id,
                    state,
                )
        elif response.status_code == 403:
            logger.error(
                "%s: Failed to authenticate job %d with token %s",
                urlparse(response.url).netloc,
                self.id,
                self.token,
            )
            if logger.headers["Job-Status"] == "canceled":
                raise JobCancelledException()
            else:
                raise AuthException()
        else:
            raise NotImplementedError(
                "Unrecognised status code from request", response, response.content
            )

        if state is not None:
            self.state = state

    def _upload_artifacts(self, artifacts):
        raise NotImplementedError()

    @property
    def id(self):
        return self._id

    @property
    def token(self):
        return self._token

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        if new_state not in ["running", "success", "failed"]:
            raise ValueError("Invalid state given " + new_state)
        if self.state != "running":
            raise AlreadyFinishedExcpetion(
                "Status cannot be changed for an " "already finished job"
            )
        self._state = new_state

    @property
    def log(self):
        return self._log

    @log.setter
    def log(self, log):
        if not isinstance(log, JobLog):
            raise TypeError("Expected JobLog but got " + type(JobLog).__name__)
        self._log = log

    @property
    def variables(self):
        return list(self._variables.values())

    @property
    def username(self):
        return self._variables["GITLAB_USER_LOGIN"].value

    @property
    def project_url(self):
        return self._variables["CI_PROJECT_URL"].value

    @property
    def project_path(self):
        return self._variables["CI_PROJECT_PATH"].value

    @property
    def project_name(self):
        return self._variables["CI_PROJECT_NAME"].value

    @property
    def ref(self):
        return self._job_info["git_info"]["ref"]

    @property
    def is_branch(self):
        return self._job_info["git_info"]["ref_type"] == "branch"

    @property
    def repo_url(self):
        return self._job_info["git_info"]["repo_url"]

    @property
    def name(self):
        return self._job_info["job_info"]["name"]

    @property
    def stage(self):
        return self._job_info["job_info"]["stage"]

    @property
    def job_url(self):
        return self._variables["CI_JOB_URL"].value

    @property
    def pipeline_url(self):
        return self._variables["CI_PIPELINE_URL"].value

    @property
    def commit_sha(self):
        return self._job_info["git_info"]["sha"]

    @property
    def commit_message(self):
        return self._variables["CI_COMMIT_MESSAGE"].value

    @property
    def pipeline_id(self):
        return self._variables["CI_PIPELINE_ID"].value

    @property
    def script(self):
        # TODO This is incomplete
        assert len(self._job_info["steps"]) in [1, 2]
        return self._job_info["steps"][0]["script"]

    @property
    def after_script(self):
        # TODO This is incomplete
        assert len(self._job_info["steps"]) in [1, 2]
        if len(self._job_info["steps"]) >= 2:
            return self._job_info["steps"][1]["script"]

    def get_registry_credential(self, image_name):
        matched = []
        for credential in self._job_info["credentials"]:
            if credential["type"] != "registry":
                continue
            if not image_name.startswith(credential["url"]):
                continue
            matched.append(credential)

        if len(matched) == 0:
            raise KeyError("No registry credential found for " + image_name)
        elif len(matched) == 1:
            return matched[0].copy()
        else:
            raise NotImplementedError(
                "Found multiple matching credentials", self._job_info["credentials"]
            )


class EnvVar(object):
    """docstring for EnvVar"""

    def __init__(self, key="unknown", value="", public=False, masked=True, **kwargs):
        """

        Raises
        ------
        ValueError: One of the properties are invalid
        """
        if not re.match(r"^[a-zA-Z0-9_]+$", key):
            raise ValueError("Environment variables must match /^[a-zA-Z0-9_]+$/")
        self._key = key

        self._value = value

        if not isinstance(public, bool):
            raise ValueError('Property "public" of EnvVar must be of type bool')
        self._is_public = public

        if not isinstance(masked, bool):
            raise ValueError('Property "masked" of EnvVar must be of type bool')
        self._is_masked = masked

        if kwargs:
            logger.error("Unrecognised EnvVar argumnets %s", repr(kwargs))

    def __repr__(self):
        if self.is_public and not self.is_masked:
            ret_val = "EnvVar(key={key}, value={value})"
        else:
            ret_val = "EnvVar(key={key})"
        return ret_val.format(key=self.key, value=self.value)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    @property
    def is_public(self):
        return self._is_public

    @property
    def is_masked(self):
        return self._is_masked

    def bash(self):
        return 'export {key}="{value}"'.format(key=self.key, value=self.value)


class JobLog(object):
    def __init__(self, job, log=None):
        self._job = job
        if log is None:
            self._log = "Running with gitlab_runner_api " + package_version + "\n"
            self._remote_length = 0
        else:
            self._log = log
            self._remote_length = len(log)

    def __str__(self):
        return self._log

    def __len__(self):
        return len(self._log)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._log == other._log
        else:
            return self._log == other

    def __add__(self, other):
        raise AttributeError("+ is not supported, use += instead")

    def __iadd__(self, other):
        if other == "":
            logger.debug("Job %d: Skipping empty log patch", self._job.id)
            return self

        logger.debug("Job %d: Appending to log: %s", self._job.id, other)
        self._log += str(other)

        # Update the log on GitLab
        headers = {
            "JOB-TOKEN": self._job.token,
            "Content-Range": str(self._remote_length)
            + "-"
            + str(len(self) - self._remote_length),
        }
        response = requests.patch(
            self._job._runner.api_url + "/api/v4/jobs/" + str(self._job.id) + "/trace",
            str(self)[self._remote_length :],
            headers=headers,
        )

        if response.status_code == 202:
            logger.info(
                "%s: Patched %d characters to Job %d",
                urlparse(response.url).netloc,
                len(other),
                self._job.id,
            )
            self._remote_length += len(other)
        elif response.status_code == 403:
            logger.error(
                "%s: Failed to authenticate job %d with token %s",
                urlparse(response.url).netloc,
                self._job.id,
                self._job.token,
            )
            if response.headers["Job-Status"] == "canceled":
                raise JobCancelledException()
            else:
                raise AuthException()
        elif response.status_code == 416:
            logger.warning(
                "%s: Failed to patch Job %d's log with %s due to "
                "invalid content range, resetting...",
                urlparse(response.url).netloc,
                self._job.id,
                headers,
            )
            self._job._update_state()
            self._remote_length = len(self._log)
        else:
            logger.warning(
                "%s: Failed apply log patch to Job %d for unknown"
                "reason. Status code: %d Content: %s",
                urlparse(response.url).netloc,
                self._job.id,
                response.status_code,
                response.content,
            )

        return self
