=================
gitlab_runner_api
=================

.. image:: https://github.com/chrisburr/gitlab-runner-api/workflows/Testing/badge.svg?branch=main
   :target: https://github.com/chrisburr/gitlab-runner-api/actions?query=branch%3Amain
   :alt: CI Status

.. image:: https://readthedocs.org/projects/gitlab-runner-api/badge/?version=latest
   :target: https://gitlab-runner-api.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. image:: https://badge.fury.io/py/gitlab-runner-api.svg
   :target: https://pypi.org/project/gitlab-runner-api/
   :alt: PyPI Package

.. image:: https://img.shields.io/conda/vn/conda-forge/gitlab-runner-api/
   :target: https://github.com/conda-forge/gitlab-runner-api-feedstock/
   :alt: Conda-forge Package

An unofficial Python implementation of the API for creating customised GitLab CI runners.

This package provides the basic functionality for registering a :class:`~gitlab_runner_api.Runner`.
This object can then be used to request a :class:`~gitlab_runner_api.Job` and communicate the log, status and artifacts back to GitLab.
No functionality is provided to execute the payloads defined in the ``.gitlab-ci.yml``.

This package was originally developed to support `LHCb's Analysis Productions <https://gitlab.cern.ch/lhcb-datapkg/AnalysisProductions>`_ by providing a CI runner that could submit jobs to LHCbDIRAC.
More details can be found in TODO.

Registering a Runner
====================

The simplest way to register a new :class:`~gitlab_runner_api.Runner` is with the included command line tool:

.. code-block::

   $ register-runner --help
   usage: register-runner [-h] [--locked] [--maximum-timeout MAXIMUM_TIMEOUT] api_url token output_fn

   positional arguments:
   api_url
   token
   output_fn

   optional arguments:
   -h, --help            show this help message and exit
   --locked              Lock the runner the to the current project
   --maximum-timeout MAXIMUM_TIMEOUT
                           Maximum timeout set when this Runner will handle the job (in seconds)

For example

.. code-block:: bash

   $ register-runner "https://gitlab.cern.ch/" "MY_REGISTRATION_TOKEN" "my-runner-data.json " --locked
   INFO:gitlab_runner_api:gitlab.cern.ch: Successfully registered runner 6602 (abcdefghij)
   INFO:gitlab_runner_api:gitlab.cern.ch: Successfully initialised runner 6602

where arguments can be found by navigating to the "CI/CD" page of the desired repository's settings.

Getting jobs
============

After a runner has been registered it can be loaded from the ``.json`` file and used to request jobs:

.. code-block:: python

   from gitlab_runner_api import Runner
   runner = Runner.load("my-runner-data.json")
   runner.check_auth()
   if job := runner.request_job():
       print("Received a new job, starting executor")
       my_job_executor(job)
   else:
       print("No jobs are currently available")

Executing jobs
==============

A minimal CI executor might run as follows:

.. code-block:: python

   from gitlab_runner_api import failure_reasons

   job.log += f"Starting job with id {job.id} for branch {job.ref}\n"
   do_clone_and_checkout(job.repo_url, job.commit_sha)
   success = run_tests(job)
   if success:
       job.log += "All tests ran successfully\n"
       job.set_success()
   else:
       # ANSI formatting codes can be used to enhance the CI logs
       job.log += "\u001b[31mJob failed!!!\u001b[0m\n"
       job.set_failed(failure_reasons.ScriptFailure())

See the reference :class:`gitlab_runner_api.Job` documentation for the full list of available properties.

Persisting jobs
===============

For long running jobs it may be desirable to persist the job object between calls.
This can be done using a similar interface to the ``pickle`` module in the Python standard library:

.. code-block:: python

   job_data = job.dumps()

   from gitlab_runner_api import Job
   job = Job.loads(job_data)

**Note:** The job log is included in the persisted data therefore the :class:`~gitlab_runner_api.Job` object cannot be persisted once and loaded multiple times without loosing the log messages.
