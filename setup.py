from os.path import join

from setuptools import setup, find_packages


# Load the README
with open(join("README.rst"), "rt") as fp:
    readme_text = fp.read()

test_requires = ["pytest", "responses", "requests-toolbelt"]

# Define the package
setup(
    use_scm_version=True,
    name="gitlab_runner_api",
    data_files=[("", ["README.rst"])],
    packages=find_packages("src"),
    package_dir={"": "src"},
    license="LICENSE.txt",
    long_description=readme_text,
    setup_requires=["setuptools_scm"],
    install_requires=["setuptools", "colorlog", "requests", "six"],
    tests_require=test_requires,
    extras_require={"testing": test_requires,},
    entry_points={
        "console_scripts": ["register-runner=gitlab_runner_api:cli.register_runner",],
    },
)
