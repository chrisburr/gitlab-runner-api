from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'ansi',
    'get_template',
    'Retrier',
]

import time

import jinja2

from ..logging import logger
from . import ansi


env = jinja2.Environment(
    loader=jinja2.PackageLoader('gitlab_runner_api'),
    undefined=jinja2.StrictUndefined
)
get_template = env.get_template


class Retrier(object):
    def __init__(self, func, to_catch, to_raise, n_retries=3, wait_seconds=5):
        self._func = func
        self._to_catch = to_catch
        self._to_raise = to_raise
        self._n_retries = n_retries
        self._wait_seconds = wait_seconds

    def __call__(self, *args, **kwargs):
        for i in range(1, self._n_retries+1):
            try:
                return self._func(*args, **kwargs)
            except self._to_catch as e:
                logger.warning(
                    'Caught error running %s on retry %d of %d, waiting %d seconds. %r',
                    self._func.__name__, i, self._n_retries, self._wait_seconds, e
                )
                time.sleep(self._wait_seconds)
        raise self._to_raise
