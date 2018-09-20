from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'Runner',
]


class Runner(object):
    def __init__(self, runner_id, description=None, active=None, locked=None,
                 run_untagged=None, tag_list=None, maximum_timeout=None,
                 name=None, version=None, revision=None, platform=None,
                 architecture=None, executor=None, features=None):
        self._id = runner_id
        self._jobs = {}

        self._description = description
        self._active = active
        self._locked = locked
        self._run_untagged = run_untagged
        self._tag_list = tag_list
        self._maximum_timeout = maximum_timeout
        # From the info parameter of the request
        self._name = name
        self._version = version
        self._revision = revision
        self._platform = platform
        self._architecture = architecture
        self._executor = executor
        # TODO From the info.features parameter of the request

    @property
    def id(self):
        return self._id

    @property
    def description(self):
        return self._description

    @property
    def active(self):
        return self._active

    @property
    def locked(self):
        return self._locked

    @property
    def run_untagged(self):
        return self._run_untagged

    @property
    def tag_list(self):
        return self._tag_list

    @property
    def maximum_timeout(self):
        return self._maximum_timeout

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def revision(self):
        return self._revision

    @property
    def platform(self):
        return self._platform

    @property
    def architecture(self):
        return self._architecture

    @property
    def executor(self):
        return self._executor
