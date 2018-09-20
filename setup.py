import os
from os.path import join

from distutils.core import setup


# Load the version
with open(join(os.getcwd(), 'gl_runner_api', 'version.py'), 'rt') as fp:
    exec(fp.read())

# Load the README
with open(join('README.rst'), 'rt') as fp:
    readme_text = fp.read()

# Define the package
setup(
    name='gl_runner_api',
    version=version,
    data_files=[('', ['README.rst'])],
    packages=['gl_runner_api', 'gl_runner_api.testing'],
    license='LICENSE.txt',
    long_description=readme_text,
    install_requires=['colorlog', 'requests', 'six'],
    tests_require=['pytest', 'responses', 'requests-toolbelt'],
)
