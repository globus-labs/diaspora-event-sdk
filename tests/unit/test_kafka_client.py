import json
import subprocess
import sys
import textwrap
import warnings
from unittest import mock

import pytest


def test_token_provider_implements_the_installed_base_class():
    kafka = pytest.importorskip("kafka")
    from diaspora_event_sdk.sdk import kafka_client

    if kafka.__version__.startswith("2."):
        from kafka.sasl.oauth import AbstractTokenProvider
    else:
        from kafka.net.sasl.oauth import AbstractTokenProvider
    assert kafka_client.kafka_available, kafka_client.kafka_import_error
    assert issubclass(kafka_client.MSKTokenProvider, AbstractTokenProvider)


def test_default_serializer_writes_json_without_warning():
    kafka = pytest.importorskip("kafka")
    from diaspora_event_sdk.sdk import kafka_client

    with (
        mock.patch.object(kafka.KafkaProducer, "__init__", return_value=None) as init,
        mock.patch.object(kafka_client, "get_diaspora_config", side_effect=dict),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error")
        producer = kafka_client.KafkaProducer("ns-1.t1")
    # what the producer's __del__ reads, as the mocked __init__ set nothing
    producer.config = {"client_id": None, "transactional_id": None}
    serializer = init.call_args.kwargs["value_serializer"]
    encode = getattr(serializer, "fn", serializer)
    assert encode({"a": 1}) == json.dumps({"a": 1}).encode()
    if not kafka.__version__.startswith("2."):
        from kafka.serializer import Serializer

        assert isinstance(serializer, Serializer)


def test_incompatible_kafka_python_names_the_supported_range(tmp_path):
    # A kafka package without kafka.errors stands in for an unsupported release.
    (tmp_path / "kafka").mkdir()
    (tmp_path / "kafka" / "__init__.py").write_text(
        "class KafkaConsumer: pass\nclass KafkaProducer: pass\n"
    )
    script = textwrap.dedent(
        """
        from diaspora_event_sdk.sdk import kafka_client
        assert not kafka_client.kafka_available
        try:
            kafka_client.KafkaProducer("t")
        except ImportError as e:
            print(e)
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script],
        env={"PYTHONPATH": f"{tmp_path}:."},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "kafka-python>=2.1,<4" in out
