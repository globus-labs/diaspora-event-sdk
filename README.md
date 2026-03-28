# Diaspora Event Fabric SDK

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/globus-labs/diaspora-event-sdk/main.svg)](https://results.pre-commit.ci/latest/github/globus-labs/diaspora-event-sdk/main)
[![Tests](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/tests.yml/badge.svg)](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/tests.yml)
[![Release](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/release.yml/badge.svg)](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/release.yml)
[![GitHub Release](https://img.shields.io/github/v/release/globus-labs/diaspora-event-sdk?color=teal)](https://github.com/globus-labs/diaspora-event-sdk/releases)
[![PyPI Version](https://img.shields.io/pypi/v/diaspora-event-sdk?color=teal)](https://pypi.org/project/diaspora-event-sdk/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/pypi/pyversions/diaspora-event-sdk.svg)](https://pypi.org/project/diaspora-event-sdk/)

## Installation

```bash
pip install "diaspora-event-sdk[kafka-python]"
```

For web service only including consumer RESTful API:

```bash
pip install diaspora-event-sdk
```

## Examples

- **[DiasporaDemo.ipynb](diaspora_event_sdk/examples/DiasporaDemo.ipynb)** — Authentication, user/key/topic management, and Kafka produce/consume
- **[ConsumerRESTDemo.ipynb](diaspora_event_sdk/examples/ConsumerRESTDemo.ipynb)** — Consumer REST API walkthrough (Confluent Kafka REST Proxy v2 compatible)

## Acknowledgment

We thank the entire team of the Diaspora Project for their helpful comments and feedback. This material is based upon work supported by the U.S. Department of Energy (DOE), Office of Science, Office of Advanced Scientific Computing Research, under Contract DE-AC02-06CH11357.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
