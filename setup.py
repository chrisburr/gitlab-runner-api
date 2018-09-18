import os
from os.path import join
import sys

from distutils.core import setup


# Load the version
sys.path.insert(0, join(os.getcwd(), 'gl_runner_api'))
from version import version

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
    install_requires=['requests'],
    tests_require=['pytest', 'responses', 'requests-toolbelt'],
)
