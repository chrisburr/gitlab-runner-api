from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from gitlab_runner_api import failure_reasons


def test_failure_baseclass():
    with pytest.raises(TypeError):
        failure_reasons._FailureReason()


def test_unknown_failure():
    reason = failure_reasons.UnknownFailure()
    assert str(reason) == "unknown_failure"


def test_script_failure():
    reason = failure_reasons.ScriptFailure()
    assert str(reason) == "script_failure"


def test_api_failure():
    reason = failure_reasons.ApiFailure()
    assert str(reason) == "api_failure"


def test_stuck_or_timeout_failure():
    reason = failure_reasons.StuckOrTimeoutFailure()
    assert str(reason) == "stuck_or_timeout_failure"


def test_runner_system_failure():
    reason = failure_reasons.RunnerSystemFailure()
    assert str(reason) == "runner_system_failure"


def test_missing_dependency_failure():
    reason = failure_reasons.MissingDependencyFailure()
    assert str(reason) == "missing_dependency_failure"
