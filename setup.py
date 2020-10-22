from os.path import join

from setuptools import setup, find_packages


# Load the README
with open(join("README.rst"), "rt") as fp:
    readme_text = fp.read()

test_requires = ["pytest", "pytest-cov", "responses", "requests-toolbelt"]

# Define the package
setup(
    use_scm_version=True,
    name="gitlab_runner_api",
    data_files=[("", ["README.rst"])],
    packages=find_packages("src"),
    package_dir={"": "src"},
    license="MIT",
    long_description=readme_text,
    url="https://github.com/chrisburr/gitlab-runner-api/",
    setup_requires=["setuptools_scm"],
    install_requires=["setuptools", "colorlog", "requests", "six"],
    tests_require=test_requires,
    extras_require={"testing": test_requires},
    entry_points={
        "console_scripts": ["register-runner=gitlab_runner_api:cli.register_runner"]
    },
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT",
    ],
    python_requires=">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*",
)
