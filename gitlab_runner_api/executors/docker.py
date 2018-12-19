from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import io
import select
import tarfile

import docker

from ..exceptions import ImagePullException
from ..failure_reasons import RunnerSystemFailure, ScriptFailure, StuckOrTimeoutFailure, UnknownFailure
from ..logging import logger
from ..utils import ansi, get_template, Retrier


class DockerContainer(object):
    def __init__(self, job):
        self._client = docker.from_env()

        self._job = job
        self._container = None

    def __enter__(self):
        if self._container is not None:
            raise RuntimeError('Nesting context managers is not supported')
        self._create_container()
        return self

    def __exit__(self, type, value, traceback):
        self._remove_container()

    @property
    def id(self):
        if self._container is None:
            raise AttributeError('DockerContainer can only be used as a context manager')
        return self._container.id

    def _get_image(self):
        image_name = self._job._job_info['image']['name']

        # See if we have credentials
        try:
            auth_config = self._job.get_registry_credential('registry')
        except KeyError:
            auth_config = None
            message = 'Pulling image {image_name}\n'
        else:
            message = 'Pulling image {image_name} with authentication\n'
        self._job.log += message.format(image_name=image_name)

        # Retry pulling the image three times if needed
        self._image = Retrier(
            self._client.images.pull,
            to_catch=docker.errors.APIError,
            to_raise=ImagePullException('Failed to pull '+image_name)
        )(image_name, auth_config=auth_config)

        self._job.log += 'Using {id} for {image_name}\n'.format(
            id=self._image.id, image_name=image_name
        )
        return self._image

    def _create_container(self):
        image = self._get_image()

        # Use tty and stdin_open so the container runs indefintely
        self._container = self._client.containers.create(
            image, command='sh', tty=True, stdin_open=True
        )
        self._job.log += 'Running in docker container: {id}\n'.format(
            id=self._container.id
        )

        self._container.start()

        return self._container

    def _remove_container(self):
        try:
            self._container.remove(force=True)
        except docker.errors.NotFound:
            logger.info('Job %d: Container %s has already been removed!',
                        self._job.id, self._container.id)
        logger.info('Job %d: Removed container %s',
                    self._job.id, self._container.id)
        self._container = None

    def _write_script(self, name):
        logger.info('Job %d: Copying %s to container %s',
                    self._job.id, name, self._container.id)
        template = get_template(name+'.j2')
        script = template.render(job=self._job, ansi=ansi)

        # Create the TarInfo object for the scipt
        file_info = tarfile.TarInfo(name='/.gitlab-runner/'+name)
        file_info.mode = 555
        file_data = io.BytesIO()
        file_data.write(script.encode('utf-8'))
        file_info.size = file_data.getbuffer().nbytes
        file_data.seek(0)

        # Convert the TarInfo to an in memory TarFile
        tar_data = io.BytesIO()
        f = tarfile.TarFile(fileobj=tar_data, mode='w')
        f.addfile(file_info, file_data)
        tar_data.seek(0)

        self._container.put_archive('/', tar_data)

    def _run_script(self, name):
        self._write_script(name)

        process = DockerProcess(self, name)
        while process.is_running:
            if process.has_output:
                self._job.log += process.read(1024*1024)

        # Make sure that all of the output has been read
        self._job.log += process.read()

        return process.exit_code


class DockerProcess(object):
    def __init__(self, container, name):
        self._container = container
        self._job = container._job
        self._client = container._client
        self._name = name
        self._exit_code = None

        logger.info('Job %d: Running %s in container %s',
                    self._job.id, self._name, self._container.id)

        self._start(['bash', '/.gitlab-runner/'+self._name])

    def _start(self, command):
        resp = self._client.api.exec_create(
            self._container.id, command, workdir='/', stdout=True, stderr=True,
            stdin=False, tty=True, privileged=False, user='', environment=None
        )
        self._id = resp['Id']

        self._socket = self._client.api.exec_start(
            self._id, detach=False, tty=True, stream=False, socket=True
        )
        self._socket._sock.setblocking(False)

    @property
    def is_running(self):
        assert self._exit_code is None, self._exit_code
        return self._client.api.exec_inspect(self._id)['Running']

    @property
    def has_output(self):
        # Check if the socket has data available
        # Allow select to block for up to a second
        readable, _, _ = select.select([self._socket], [], [], 1)
        return bool(readable)

    def read(self, max_bytes=-1):
        return self._socket.read(max_bytes).decode('utf-8')

    @property
    def exit_code(self):
        if self._exit_code is None:
            if self.is_running:
                raise AttributeError('Exit code is not yet available')
            self._exit_code = self._client.api.exec_inspect(self._id)['ExitCode']
            logger.info('Job %d: Exit code from %s was %s',
                        self._job.id, self._name, self._exit_code)
        return self._exit_code


class DockerExecutor(object):
    def __init__(self, job):
        self._job = job

    def run(self):
        with DockerContainer(self._job) as container:
            exit_code = container._run_script('setup_repo.sh')
            if exit_code != 0:
                self._job.set_failed(RunnerSystemFailure())
                return

            exit_code = container._run_script('download_artifacts.sh')
            if exit_code != 0:
                self._job.set_failed(RunnerSystemFailure())
                return

            job_exit_code = container._run_script('run_job.sh')

            exit_code = container._run_script('run_after_script.sh')
            if exit_code != 0:
                self._job.log += ansi.BOLD_YELLOW+'WARNING: Got non-zero status code ('+job_exit_code+') when running after_script\n'+ansi.RESET

            exit_code = container._run_script('upload_artifacts.sh')

            if job_exit_code == 0:
                self._job.set_success()
            else:
                self._job.log += ansi.BOLD_RED+'ERROR: Got non-zero status code ('+job_exit_code+') when running job\n'+ansi.RESET
                self._job.set_failed(failure_reason=ScriptFailure())
