import json
import time
import warnings
from typing import Any, Dict

from .aws_iam_msk import generate_auth_token
from .client import Client

# If kafka-python is not installed, Kafka functionality is not available through diaspora-event-sdk.
kafka_available = True
try:
    import os

    from kafka import KafkaConsumer as KCons  # type: ignore[import,import-not-found]
    from kafka import KafkaProducer as KProd  # type: ignore[import,import-not-found]
    from kafka.sasl.oauth import (
        AbstractTokenProvider,  # type: ignore[import,import-not-found]
    )

    class MSKTokenProvider(AbstractTokenProvider):
        def token(self):
            token, _ = generate_auth_token("us-east-1")
            return token
except Exception:
    kafka_available = False


def get_diaspora_config(extra_configs: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Retrieve default Diaspora event fabric connection configurations for Kafka clients.
    Merges default configurations with custom ones provided.
    """

    try:
        if (
            "OCTOPUS_AWS_ACCESS_KEY_ID" not in os.environ
            or "OCTOPUS_AWS_SECRET_ACCESS_KEY" not in os.environ
            or "OCTOPUS_BOOTSTRAP_SERVERS" not in os.environ
        ):
            keys = Client().retrieve_key()
            os.environ["OCTOPUS_AWS_ACCESS_KEY_ID"] = keys["access_key"]
            os.environ["OCTOPUS_AWS_SECRET_ACCESS_KEY"] = keys["secret_key"]
            os.environ["OCTOPUS_BOOTSTRAP_SERVERS"] = keys["endpoint"]

    except Exception as e:
        raise RuntimeError("Failed to retrieve Kafka keys") from e

    conf = {
        "bootstrap_servers": os.environ["OCTOPUS_BOOTSTRAP_SERVERS"],
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "OAUTHBEARER",
        "api_version": (3, 5, 1),
        "sasl_oauth_token_provider": MSKTokenProvider(),
    }
    conf.update(extra_configs)
    return conf


if kafka_available:

    class KafkaProducer(KProd):
        """
        Wrapper around KProd that:
        - Requires at least one topic
        - Sets a default JSON serializer
        - Blocks until all topics have partition metadata
        """

        def __init__(self, *topics, **configs):
            if not topics:
                raise ValueError("KafkaProducer requires at least one topic")
            self.topics = topics

            configs.setdefault(
                "value_serializer",
                lambda v: json.dumps(v).encode("utf-8"),
            )

            super().__init__(**get_diaspora_config(configs))
            self._block_until_ready()

        def _block_until_ready(self) -> None:
            """
            Verify that all topics have partition metadata.

            For each topic in ``self.topics``, fetches partition metadata and checks that
            partition 0 exists. Raises ``RuntimeError`` if any topic does not yet have
            partition metadata.
            """
            for topic in self.topics:
                partitions = self.partitions_for(topic)
                if not partitions or 0 not in partitions:
                    raise RuntimeError(f"Topic {topic!r} has no partition metadata yet")

    class KafkaConsumer(KCons):
        def __init__(self, *topics, **configs):
            if not topics:
                raise ValueError("KafkaProducer requires at least one topic")
            self.topics = topics

            super().__init__(*topics, **get_diaspora_config(configs))
            self._block_until_ready()

        def _block_until_ready(self) -> None:
            """
            Verify that all topics have partition metadata.

            For each topic in ``self.topics``, fetches partition metadata and checks that
            partition 0 exists. Raises ``RuntimeError`` if any topic does not yet have
            partition metadata.
            """
            for topic in self.topics:
                partitions = self.partitions_for_topic(topic)
                if not partitions or 0 not in partitions:
                    raise RuntimeError(f"Topic {topic!r} has no partition metadata yet")


else:
    # Create dummy classes that issue a warning when instantiated
    class KafkaProducer:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            warnings.warn(
                "KafkaProducer is not available. Initialization is a no-op.",
                RuntimeWarning,
            )

    class KafkaConsumer:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            warnings.warn(
                "KafkaConsumer is not available. Initialization is a no-op.",
                RuntimeWarning,
            )


def create_producer(*topics, **kwargs) -> KafkaProducer:
    """
    Create a KafkaProducer for the given topics, with a fast initial attempt.

    This method first tries to create a producer immediately using existing
    credentials—useful when topics are already ready and the key is valid.
    If that attempt fails (e.g., missing or expired key, metadata not ready),
    the method regenerates the key once and then retries producer creation
    every 0.5 seconds until successful.

    Parameters
    ----------
    topics : list[str] or str
        Topic or list of topics to which the producer will publish.

    Returns
    -------
    KafkaProducer
        A ready KafkaProducer instance.
    """
    # --- Fast path: try with current credentials ---
    try:
        return KafkaProducer(*topics, **kwargs)
    except Exception as e:
        print(f"Initial producer creation failed: {e}")

    # --- Slow path: refresh key and retry until ready ---
    print(f"Create key: {Client().create_key()}")

    while True:
        try:
            return KafkaProducer(*topics, **kwargs)
        except Exception as e:
            print(f"Retrying producer creation: {e}")
            time.sleep(0.5)


def create_consumer(*topics, **kwargs) -> KafkaConsumer:
    """
    Create a KafkaConsumer for the given topics, mirroring create_producer() logic.

    Fast-path: try to create a consumer immediately using existing credentials.
    Slow-path: regenerate key once and retry every 0.5s until successful.

    Parameters
    ----------
    topics : list[str] or str
        Topic or list of topics to subscribe to.

    kwargs : dict
        Additional arguments passed to KafkaConsumer (e.g., auto_offset_reset).

    Returns
    -------
    KafkaConsumer
        A ready KafkaConsumer instance.
    """
    # --- Fast path: try with current credentials ---
    try:
        return KafkaConsumer(*topics, **kwargs)
    except Exception as e:
        print(f"Initial consumer creation failed: {e}")

    # --- Slow path: refresh key and retry until ready ---
    print(f"Create key: {Client().create_key()}")

    while True:
        try:
            return KafkaConsumer(*topics, **kwargs)
        except Exception as e:
            print(f"Retrying consumer creation: {e}")
            time.sleep(0.5)


# TODO: mypy diaspora_event_sdk/sdk/kafka_client.py --disallow-untyped-defs
def block_until_ready(max_minutes=5):
    """
    Test Kafka producer and consumer connections.
    By default, this method blocks for five minutes before giving up.
    It returns a boolean that indicates whether the connections can be successfully established.
    """

    def producer_connection_test(result):
        try:
            producer = KafkaProducer("__connection_test", max_block_ms=10 * 1000)
            future = producer.send(
                topic="__connection_test",
                value={"message": "Synchronous message from Diaspora SDK"},
            )
            result["producer_connection_test"] = future.get(timeout=10)
        except Exception as e:
            raise e
            print(e)

    def consumer_connection_test(result):
        try:
            consumer = KafkaConsumer(
                "__connection_test",
                consumer_timeout_ms=10 * 1000,
                auto_offset_reset="earliest",
            )
            for msg in consumer:
                result["consumer_connection_test"] = msg
                break
        except Exception as e:
            raise e
            print(e)

    result, retry_count = {}, 0
    start_time = time.time()
    while len(result) < 2:  # two tests
        if retry_count > 0:
            print(
                f"Block until connected or timed out ({max_minutes} minutes)... retry count:",
                retry_count,
                ", time passed:",
                int(time.time() - start_time),
                "seconds",
            )
        producer_connection_test(result)
        consumer_connection_test(result)
        retry_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_minutes * 60:
            print("Time limit exceeded. Exiting loop.")
            return False
    return True
