from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import io
import select
import tarfile

import docker
import jinja2

from ..exceptions import ImagePullException
from ..logging import logger
from ..utils import ansi

env = jinja2.Environment(
    loader=jinja2.PackageLoader('gitlab_runner_api'),
    undefined=jinja2.StrictUndefined
)


class Retrier(object):
    def __init__(self, func, to_catch, to_raise, n_retries=3):
        self._func = func
        self._to_catch = to_catch
        self._to_raise = to_raise
        self._n_retries = n_retries

    def __call__(self, *args, **kwargs):
        for i in range(self._n_retries):
            try:
                return self._func(*args, **kwargs)
            except self._to_catch:
                logger.warn('Caught error running %s, retry %d of %d',
                            self._func.__name__, i, self._n_retries)
        raise self._to_raise


class DockerExecutor(object):
    def __init__(self, job):
        self._job = job
        self._client = docker.from_env()

        self._image = None
        self._container = None

    @property
    def image(self):
        if self._image is None:
            image_name = self._job._job_info['image']['name']
            try:
                auth_config = self._job.get_credential('registry')
            except KeyError:
                auth_config = None
                logger.info('Job %d: Pulling image %s',
                            self._job.id, image_name)
            else:
                logger.info('Job %d: Pulling image %s with authentication',
                            self._job.id, image_name)
            self._image = Retrier(
                self._client.images.pull,
                to_catch=docker.errors.APIError,
                to_raise=ImagePullException('Failed to pull '+image_name)
            )(image_name, auth_config=auth_config)
        return self._image

    @property
    def container(self):
        if self._container is None:
            # Use tty and stdin_open so the container runs indefintely
            self._container = self._client.containers.create(
                self.image, command='sh', tty=True, stdin_open=True
            )
        return self._container

    def reset_container(self):
        if self._container is not None:
            self._container.remove(force=True)
            del self._container

    def write_script(self, name):
        template = env.get_template(name+'.j2')
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

        self.container.put_archive('/', tar_data)

    def _exec(self, command, workdir='/'):
        resp = self._client.api.exec_create(
            self.container.id, command, workdir=workdir,
            stdout=True, stderr=True, stdin=False, tty=True, privileged=False,
            user='', environment=None
        )
        my_socket = self._client.api.exec_start(
            resp['Id'], detach=False, tty=True, stream=False, socket=True
        )
        my_socket._sock.setblocking(False)
        while self._client.api.exec_inspect(resp['Id'])['Running']:
            # Check if the socket has data available
            # Allow select to block for up to a second
            readable, _, _ = select.select([my_socket], [], [], 1)
            if readable:
                print(my_socket.read(1024*1024).decode('utf-8'), end='')
        print(my_socket.read().decode('utf-8'), end='')

        exit_code = self._client.api.exec_inspect(resp['Id'])['ExitCode']
        print('Exit code was', exit_code)
        if exit_code != 0:
            raise RuntimeError(exit_code)
        return exit_code

    def run(self):
        self.container.start()

        self.write_script('setup_repo.sh')
        self._exec(['bash', '/.gitlab-runner/setup_repo.sh'])

        self.write_script('download_artifacts.sh')
        self._exec(['bash', '/.gitlab-runner/download_artifacts.sh'])

        self.write_script('run_job.sh')
        self._exec(['bash', '/.gitlab-runner/run_job.sh'])

        self.write_script('run_after_script.sh')
        self._exec(['bash', '/.gitlab-runner/run_after_script.sh'])

        self.write_script('upload_artifacts.sh')
        self._exec(['bash', '/.gitlab-runner/upload_artifacts.sh'])
