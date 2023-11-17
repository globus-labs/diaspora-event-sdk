from setuptools import setup, find_packages
from diaspora_event_sdk.version import __version__
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='diaspora_event_sdk',
    version=__version__,
    description='SDK of Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,  # This flag is used to include non-code files
    license='LICENSE',  # Specify the path to your LICENSE file
    url='https://github.com/globus-labs/diaspora_event_sdk',
    install_requires=[
        'kafka-python',
    ],
)
