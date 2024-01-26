import os
import re
from pathlib import Path

from setuptools import setup, find_packages

TEST_REQUIRES = ["pytest", "pytest-cov", "coverage", "mypy", "tox", "check-manifest"]


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
    description="SDK of Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    license="LICENSE",
    url="https://github.com/globus-labs/diaspora-event-sdk",
    install_requires=[
        "globus-sdk>=3.20.1,<4",
    ],
    extras_require={
        "kafka-python": ["kafka-python", "aws-msk-iam-sasl-signer-python"],
        "test": TEST_REQUIRES,
    },
)
