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

The `kafka-python` extra installs kafka-python, which the SDK's `KafkaProducer` and `KafkaConsumer` need. It accepts `kafka-python>=2.1,<3`: release 2.1 or a later 2.x. With kafka-python 3 installed, `KafkaProducer` and `KafkaConsumer` raise `ImportError`. kafka-python 3.0.11 does not apply `allow_auto_create_topics=False`, skips a consumer's auto-commit on `unsubscribe()`, and leaves a producer using a full CPU core once a topic it wrote to is deleted.

To use only the web service, including producing and consuming over REST, install the SDK without the extra:

```bash
pip install diaspora-event-sdk
```

## Produce and consume over REST

The web service produces and consumes records over HTTPS with your Globus login, so a client needs no Kafka client and no access key. `Client.produce` and `Client.produce_batch` send records to the produce routes, which take the request bodies of Confluent's REST API v3. `RESTConsumer` wraps the consumer routes, which take the paths and bodies of Confluent REST Proxy v2 under `/api/v2/consumers`. Name topics and consumer groups without your namespace (`Client().namespace`): the service adds it, so the group `my-group` is the Kafka consumer group `<namespace>.my-group`.

```python
from diaspora_event_sdk import Client, RESTConsumer

c = Client()
c.create_topic("my-topic")
c.produce("my-topic", {"step": 1, "loss": 0.52}, key="job-42")
c.produce_batch("my-topic", [{"value": {"step": 2}}, {"value": "done"}])

with RESTConsumer("my-group", client=c, format="json", auto_offset_reset="earliest") as consumer:
    consumer.subscribe(["my-topic"])
    for record in consumer.fetch(timeout_ms=5000):
        print(record["offset"], record["key"], record["value"])
    consumer.commit()
```

`Client.produce` writes a value of bytes as `BINARY`, and anything else, a `str` included, as `JSON`, which `json.loads` reads back the same as the SDK's `KafkaProducer` output: `produce(topic, "done")` writes the JSON string `"done"`. The bytes differ, since the service writes compact JSON and `KafkaProducer`'s default serializer adds spaces after `,` and `:`. That serializer also refuses bytes, which `produce` sends as `BINARY`. A key of bytes is sent as `BINARY`, a `str` as `STRING` (plain text), and anything else as `JSON`. The `value_type` and `key_type` arguments (`"BINARY"`, `"JSON"` or `"STRING"`) choose the type instead. Each record of `Client.produce_batch` is a dict of the same arguments (`value`, `key`, `headers`, `timestamp`, `value_type` and `key_type`) with an optional `id`.

A produce request is retried only when the service refuses it before sending the record (429 or 503) or when no connection was made. Any other error raises, since the record may have been written.

A consumer's `format` is `binary`, the default, or `json`. A `binary` consumer returns keys and values as bytes. A `json` consumer returns a key or value that is one JSON value as that value, and other text as `str`: a `STRING` key `"42"` comes back as the number 42. Header values are bytes in both formats.

The service drops consumer instances when it is deployed or restarted, and closes an instance idle for 5 minutes, which includes the time your code spends processing a fetch's records. `RESTConsumer` then creates the instance again with the same name and settings, subscribes or assigns as before, and retries the request once. The new instance starts from the group's committed offsets, so records fetched since the last commit can be fetched again. A `commit()` without offsets would commit the new instance's positions, which hold nothing fetched. So when the records fetched since the last commit came from an instance that is gone, whichever request found it gone, `commit()` sends nothing and raises `CommitLostError`, and the next fetch resumes at the group's last commit. A `commit()` with offsets on a new subscribed instance raises `CommitLostError` too: that instance gets its partitions at its first fetch, so commit the offsets again after a fetch.

`RESTConsumer` needs version 0.7.0 or later of the web service. The [service's API reference](https://github.com/haochenpan/diaspora-service/blob/main/docs/web/api.md) gives every route, limit and error code.

## Examples

- **[DiasporaDemo.ipynb](diaspora_event_sdk/examples/DiasporaDemo.ipynb)** — Authentication, user/key/topic management, and Kafka produce/consume
- **[ConsumerRESTDemo.ipynb](diaspora_event_sdk/examples/ConsumerRESTDemo.ipynb)** — Produce and consume over REST, first with raw HTTP requests and then with the SDK

## Acknowledgment

We thank the entire team of the Diaspora Project for their helpful comments and feedback. This material is based upon work supported by the U.S. Department of Energy (DOE), Office of Science, Office of Advanced Scientific Computing Research, under Contract DE-AC02-06CH11357.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
