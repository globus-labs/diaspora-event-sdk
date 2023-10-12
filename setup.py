from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='diaspora_logger',
    version='0.0.2',
    description='A Python logging library for sending logs to Diaspora Streams (Kafka)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    url='https://github.com/globus-labs/diaspora_logger',
    install_requires=[
        'kafka-python',
    ],
)
