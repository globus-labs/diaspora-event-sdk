import os
import re
from pathlib import Path

from setuptools import find_packages, setup

TEST_REQUIRES = [
    "pytest",
    "pytest-cov",
    "coverage",
    "mypy",
    "tox",
    "check-manifest",
    "pre-commit",
]


def parse_version():
    # single source of truth for package version
    version_string = ""
    version_pattern = re.compile(r'__version__ = "([^"]*)"')
    with open(os.path.join("diaspora_event_sdk", "version.py")) as f:
        for line in f:
            match = version_pattern.match(line)
            if match:
                version_string = match.group(1)
                break
    if not version_string:
        raise RuntimeError("Failed to parse version information")
    return version_string


directory = Path(__file__).parent
long_description = (directory / "README.md").read_text()

setup(
    name="diaspora-event-sdk",
    version=parse_version(),
    description="Diaspora Event Fabric SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    license="Apache 2.0",
    url="https://github.com/globus-labs/diaspora-event-sdk",
    install_requires=[
        "globus-sdk>=3.20.1,<4",
    ],
    extras_require={
        "kafka-python": ["kafka-python"],
        "test": TEST_REQUIRES,
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
