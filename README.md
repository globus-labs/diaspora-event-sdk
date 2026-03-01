# Diaspora Event Fabric SDK

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/globus-labs/diaspora-event-sdk/main.svg)](https://results.pre-commit.ci/latest/github/globus-labs/diaspora-event-sdk/main)
[![Tests](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/tests.yml/badge.svg)](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/tests.yml)
[![Release](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/release.yml/badge.svg)](https://github.com/globus-labs/diaspora-event-sdk/actions/workflows/release.yml)
[![GitHub Release](https://img.shields.io/github/v/release/globus-labs/diaspora-event-sdk?color=teal)](https://github.com/globus-labs/diaspora-event-sdk/releases)
[![PyPI Version](https://img.shields.io/pypi/v/diaspora-event-sdk?color=teal)](https://pypi.org/project/diaspora-event-sdk/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/pypi/pyversions/diaspora-event-sdk.svg)](https://pypi.org/project/diaspora-event-sdk/)


## Installation Guide
### Recommended Method: With `kafka-python`
To integrate with Diaspora Event Fabric using `KafkaProducer` and `KafkaConsumer`, install the SDK with `kafka-python`:
```bash
pip install "diaspora-event-sdk[kafka-python]"
```

## Using Diaspora Event Fabric SDK
Check out the examples in [`diaspora_event_sdk/examples/`](diaspora_event_sdk/examples/):
- [DiasporaDemoV3.ipynb](diaspora_event_sdk/examples/DiasporaDemoV3.ipynb) — Quickstart notebook covering user/key/topic management and Kafka produce/consume
- [reliable_client_creation_examples.ipynb](diaspora_event_sdk/examples/reliable_client_creation_examples.ipynb) — Reliable client creation with retry logic
