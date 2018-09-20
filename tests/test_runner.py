from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import pytest
import tempfile

from gl_runner_api import AuthException, Runner
from gl_runner_api.testing import FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use()
def test_register_without_parameters(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    check_runner(gitlab_api, runner)


@gitlab_api.use()
def test_register_with_parameters(gitlab_api):
    runner = Runner.register(
        'https://gitlab.cern.ch', gitlab_api.token,
        name='The runner name',
        description='The runner description',
        active=True,
        locked=False,
        run_untagged=True,
        tags=['dirac', 'docker', 'cvmfs'],
        maximum_timeout=24*60*60,
        version='1.0',
        revision='a94b1e',
        platform='linux',
        architecture='x86_64',
        executor='dirac'
    )
    check_runner(gitlab_api, runner)


@gitlab_api.use()
def test_equality(gitlab_api):
    runner_1 = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    runner_2 = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    assert runner_1 == runner_1
    assert runner_2 == runner_2
    assert runner_1 != runner_2


@gitlab_api.use()
def test_repr(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    print(repr(runner))
    assert runner.token in repr(runner)


@gitlab_api.use()
def test_serialise(gitlab_api):
    runner = Runner.register(
        'https://gitlab.cern.ch', gitlab_api.token,
        name='The runner name',
        description='The runner description',
        active=True,
        locked=False,
        run_untagged=True,
        tags=['dirac', 'docker', 'cvmfs'],
        maximum_timeout=24*60*60,
        version='1.0',
        revision='a94b1e',
        platform='linux',
        architecture='x86_64',
        executor='dirac'
    )

    as_string = runner.dumps()
    runner_from_string = Runner.loads(as_string)
    assert runner == runner_from_string

    with tempfile.NamedTemporaryFile() as fp:
        runner.dump(fp.name)
        runner_from_file = Runner.load(fp.name)
    assert runner == runner_from_file


@gitlab_api.use()
def test_serialise_invalid_version(gitlab_api):
    runner = Runner.register('https://gitlab.cern.ch', gitlab_api.token)
    serialised_runner = json.loads(runner.dumps())
    serialised_runner[0] = 2
    as_string = json.dumps(serialised_runner)

    with pytest.raises(ValueError):
        Runner.loads(as_string)

    with tempfile.NamedTemporaryFile(mode='wt') as fp:
        json.dump(as_string, fp)
        fp.flush()
        with pytest.raises(ValueError):
            Runner.load(fp.name)


@gitlab_api.use()
def test_bad_init(gitlab_api):
    with pytest.raises(AuthException):
        Runner('https://gitlab.cern.ch', 1, 'invalid_token', {})


@gitlab_api.use()
def test_invalid_token(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', 500)
    with pytest.raises(AuthException):
        Runner.register('https://gitlab.cern.ch', 'invalid_token')


@gitlab_api.use()
def test_invalid_name(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, name=[])


@gitlab_api.use()
def test_invalid_description(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, description=[])


@gitlab_api.use()
def test_invalid_active(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, active='True')


@gitlab_api.use()
def test_invalid_locked(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, locked='True')


@gitlab_api.use()
def test_invalid_run_untagged(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, run_untagged='True')


@gitlab_api.use()
def test_invalid_tags(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, tags='a,b,c')
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, tags=['a', 'ab,c'])


@gitlab_api.use()
def test_invalid_maximum_timeout(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, maximum_timeout='100')


@gitlab_api.use()
def test_invalid_version(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, version=5)


@gitlab_api.use()
def test_invalid_revision(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, revision=1)


@gitlab_api.use()
def test_invalid_platform(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, platform=[])


@gitlab_api.use()
def test_invalid_architecture(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, architecture=[])


@gitlab_api.use()
def test_invalid_executor(gitlab_api):
    with pytest.raises(ValueError):
        Runner.register('https://gitlab.cern.ch', gitlab_api.token, executor=[])


def check_runner(gitlab_api, runner):
    assert runner.api_url == 'https://gitlab.cern.ch'
    assert runner.token in gitlab_api._runners
    backend_runner = gitlab_api._runners[runner.token]
    assert runner.id == int(backend_runner.id)
    assert runner.name == backend_runner.name
    assert runner.description == backend_runner.description
    with pytest.raises(NotImplementedError):
        runner.active
    assert runner.locked == backend_runner.locked
    assert runner.run_untagged == backend_runner.run_untagged
    if backend_runner.tag_list is None:
        assert runner.tags == []
    else:
        assert runner.tags == set(backend_runner.tag_list)
    assert runner.maximum_timeout == backend_runner.maximum_timeout
    assert runner.version == backend_runner.version
    assert runner.revision == backend_runner.revision
    assert runner.platform == backend_runner.platform
    assert runner.architecture == backend_runner.architecture
    assert runner.executor == backend_runner.executor
