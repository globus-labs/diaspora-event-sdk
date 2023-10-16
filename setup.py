from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='diaspora_logger',
    version='0.0.5',
    description='A Python logging library for sending logs to Diaspora Streams (Kafka)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,  # This flag is used to include non-code files
    license='LICENSE',  # Specify the path to your LICENSE file
    url='https://github.com/globus-labs/diaspora_logger',
    install_requires=[
        'kafka-python',
    ],
)
