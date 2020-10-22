from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from gitlab_runner_api.job import EnvVar


def test_public():
    var = EnvVar("the_key", "The value\nsomethig", True)
    assert var.key == "the_key"
    assert var.value == "The value\nsomethig"
    assert var.is_public is True

    assert var.key in repr(var)
    assert var.value in repr(var)


def test_private():
    var = EnvVar("the_key", "The value\nsomethig", False)
    assert var.key == "the_key"
    assert var.value == "The value\nsomethig"
    assert var.is_public is False
    assert var.key in repr(var)
    assert var.value not in repr(var)


def test_bad_key():
    bad_values = [
        "cd /home",
        "PATH''s",
        "PYTHONPATH;a",
    ]
    for key in bad_values:
        with pytest.raises(ValueError):
            EnvVar(key, "The value\nsomethig", False)


def test_bad_is_public():
    bad_values = [
        "true",
        "false",
        "True",
        "false",
        0,
        1,
    ]
    for is_public in bad_values:
        with pytest.raises(ValueError):
            EnvVar("key", "The value\nsomethig", is_public)
