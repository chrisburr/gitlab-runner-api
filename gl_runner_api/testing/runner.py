from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'Runner',
]


class Runner(object):
    def __init__(self, runner_id):
        self._id = runner_id
        self._jobs = {}

    @property
    def id(self):
        return self._id
