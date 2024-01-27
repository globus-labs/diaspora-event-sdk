import json
from typing import Dict, Any
import warnings
import time

from .client import Client

# If kafka-python is not installed, Kafka functionality is not available through diaspora-event-sdk.
kafka_available = True
try:
    from kafka import KafkaProducer as KProd  # type: ignore[import,import-not-found]
    from kafka import KafkaConsumer as KCons  # type: ignore[import,import-not-found]
    from aws_msk_iam_sasl_signer import MSKAuthTokenProvider  # type: ignore[import,import-not-found]
    import os

    class MSKTokenProvider:
        def token(self):
            token, _ = MSKAuthTokenProvider.generate_auth_token("us-east-1")
            return token
except ImportError:
    kafka_available = False


def get_diaspora_config(extra_configs: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Retrieve default Diaspora event fabric connection configurations for Kafka clients.
    Merges default configurations with custom ones provided.
    """
    try:
        keys = Client().retrieve_key()
        os.environ["AWS_ACCESS_KEY_ID"] = keys["access_key"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = keys["secret_key"]
    except Exception as e:
        raise RuntimeError("Failed to retrieve Kafka keys") from e

    conf = {
        "bootstrap_servers": keys["endpoint"],
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "OAUTHBEARER",
        "api_version": (3, 5, 1),
        "sasl_oauth_token_provider": MSKTokenProvider(),
    }
    conf.update(extra_configs)
    return conf


if kafka_available:

    class KafkaProducer(KProd):
        def __init__(self, **configs):
            configs.setdefault(
                "value_serializer", lambda v: json.dumps(v).encode("utf-8")
            )
            super().__init__(**get_diaspora_config(configs))

    class KafkaConsumer(KCons):
        def __init__(self, *topics, **configs):
            super().__init__(*topics, **get_diaspora_config(configs))

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


# TODO: mypy diaspora_event_sdk/sdk/kafka_client.py --disallow-untyped-defs
def block_until_ready(max_minutes=5):
    """
    Test Kafka producer and consumer connections.
    By default, this method blocks for five minutes before giving up.
    It returns a boolean that indicates whether the connections can be successfully established.
    """

    def producer_connection_test(result):
        try:
            producer = KafkaProducer(max_block_ms=10 * 1000)
            future = producer.send(
                topic="__connection_test",
                value={"message": "Synchronous message from Diaspora SDK"},
            )
            result["producer_connection_test"] = future.get(timeout=10)
        except Exception as e:
            pass

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
            pass

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
