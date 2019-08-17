from os.path import join

from setuptools import setup, find_packages


# Load the README
with open(join('README.rst'), 'rt') as fp:
    readme_text = fp.read()

# Define the package
setup(
    use_scm_version=True,
    name='gitlab_runner_api',
    data_files=[('', ['README.rst'])],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    license='LICENSE.txt',
    long_description=readme_text,
    install_requires=['colorlog', 'requests', 'six', 'docker', 'jinja2'],
    tests_require=['pytest', 'responses', 'requests-toolbelt'],
)
