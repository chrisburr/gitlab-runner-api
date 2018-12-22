from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

import gitlab_runner_api


class ExampleException1(Exception):
    pass


class ExampleException2(Exception):
    pass


def get_example_function(n_times_to_fail=2):
    def example_func():
        example_func.n_tries += 1
        print('Have tried', example_func.n_tries, 'times')
        if example_func.n_tries <= n_times_to_fail:
            raise ExampleException1()

    example_func.n_tries = 0
    return example_func


def test_retrier_good():
    example_func = get_example_function()
    gitlab_runner_api.utils.Retrier(
        example_func, ExampleException1, ExampleException2('My message'),
        wait_seconds=0
    )()


def test_retrier_bad():
    example_func = get_example_function(n_times_to_fail=4)

    with pytest.raises(ExampleException2, match='My message'):
        gitlab_runner_api.utils.Retrier(
            example_func, ExampleException1, ExampleException2('My message'),
            n_retries=4, wait_seconds=0
        )()
    assert example_func.n_tries == 4
