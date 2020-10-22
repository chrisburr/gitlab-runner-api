from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    "ApiFailure",
    "MissingDependencyFailure",
    "RunnerSystemFailure",
    "ScriptFailure",
    "StuckOrTimeoutFailure",
    "UnknownFailure",
]

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class _FailureReason:
    @abc.abstractmethod
    def __str__(self):
        """String corresponding to the GitLab API's name for this method"""


class ApiFailure(_FailureReason):
    def __str__(self):
        return "api_failure"


class MissingDependencyFailure(_FailureReason):
    def __str__(self):
        return "missing_dependency_failure"


class RunnerSystemFailure(_FailureReason):
    def __str__(self):
        return "runner_system_failure"


class ScriptFailure(_FailureReason):
    def __str__(self):
        return "script_failure"


class StuckOrTimeoutFailure(_FailureReason):
    def __str__(self):
        return "stuck_or_timeout_failure"


class UnknownFailure(_FailureReason):
    def __str__(self):
        return "unknown_failure"
