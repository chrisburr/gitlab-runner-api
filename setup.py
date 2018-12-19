import os
from os.path import join

from distutils.core import setup


# Load the version
with open(join(os.getcwd(), 'gitlab_runner_api', 'version.py'), 'rt') as fp:
    exec(fp.read())

# Load the README
with open(join('README.rst'), 'rt') as fp:
    readme_text = fp.read()

# Define the package
setup(
    name='gitlab_runner_api',
    version=version,
    data_files=[('', ['README.rst'])],
    packages=['gitlab_runner_api', 'gitlab_runner_api.testing'],
    license='LICENSE.txt',
    long_description=readme_text,
    install_requires=['colorlog', 'requests', 'six', 'docker', 'jinja2'],
    tests_require=['pytest', 'responses', 'requests-toolbelt'],
)
