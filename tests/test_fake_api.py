from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pytest

from gitlab_runner_api.testing import FakeGitlabAPI


gitlab_api = FakeGitlabAPI()


@gitlab_api.use(n_runners=2, n_running=3)
def test_repr(gitlab_api):
    job = gitlab_api.running_jobs[2]
    print(repr(job))
    assert 'id='+str(job.id) in repr(job)
    assert 'status=running' in repr(job)


@gitlab_api.use(n_runners=2, n_pending=3, n_running=4)
def test_setting_job_failure_reason(gitlab_api):
    job = gitlab_api.running_jobs[1]
    with pytest.raises(ValueError):
        job.failure_reason = 'invalid_reason'


def test_request_init_with_artifacts(caplog):
    @gitlab_api.use(n_runners=2, n_pending=3, n_success=4, n_failed=4, n_with_artifacts=5)
    def tmp(gitlab_api):
        n = 0
        for job in gitlab_api.completed_jobs:
            if job.file_data is not None:
                n += 1
        assert n == 5
    tmp(caplog)

    with pytest.raises(ValueError):
        @gitlab_api.use(n_runners=2, n_pending=3, n_running=4, n_with_artifacts=1)
        def tmp(gitlab_api):
            pass
        tmp(caplog)

    with pytest.raises(ValueError):
        @gitlab_api.use(n_runners=2, n_success=2, n_with_artifacts=3)
        def tmp(gitlab_api):
            pass
        tmp(caplog)

    with pytest.raises(ValueError):
        @gitlab_api.use(n_runners=2, n_failed=3, n_with_artifacts=4)
        def tmp(gitlab_api):
            pass
        tmp(caplog)
