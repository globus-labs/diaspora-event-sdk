import json
import logging
import time
import uuid
import warnings
from typing import Any, Dict

from .aws_iam_msk import generate_auth_token
from .client import Client

# File-level logger
logger = logging.getLogger(__name__)

# If kafka-python is not installed, Kafka functionality is not available through diaspora-event-sdk.
kafka_available = True
try:
    import os

    from kafka import KafkaConsumer as KCons  # type: ignore[import,import-not-found]
    from kafka import KafkaProducer as KProd  # type: ignore[import,import-not-found]
    from kafka.errors import KafkaTimeoutError, TopicAuthorizationFailedError  # type: ignore[import,import-not-found]
    from kafka.sasl.oauth import (
        AbstractTokenProvider,  # type: ignore[import,import-not-found]
    )

    class MSKTokenProvider(AbstractTokenProvider):
        def token(self):
            token, _ = generate_auth_token("us-east-1")
            return token
except Exception:
    kafka_available = False
    # Fallback if kafka-python is not available
    TopicAuthorizationFailedError = Exception
    KafkaTimeoutError = Exception


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
            client = Client()
            keys = client.get_key()
            os.environ["OCTOPUS_AWS_ACCESS_KEY_ID"] = keys["access_key"]
            os.environ["OCTOPUS_AWS_SECRET_ACCESS_KEY"] = keys["secret_key"]
            os.environ["OCTOPUS_BOOTSTRAP_SERVERS"] = keys["endpoint"]

    except Exception as e:
        raise RuntimeError("Failed to retrieve Kafka keys") from e

    conf = {
        "bootstrap_servers": os.environ["OCTOPUS_BOOTSTRAP_SERVERS"],
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "OAUTHBEARER",
        "api_version": (3, 8, 1),
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
        - Does NOT block until topics have partition metadata
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
            # Note: We do NOT block on metadata here

    class KafkaConsumer(KCons):
        def __init__(self, *topics, **configs):
            if not topics:
                raise ValueError("KafkaConsumer requires at least one topic")
            self.topics = topics

            super().__init__(*topics, **get_diaspora_config(configs))
            # Note: We do NOT block on metadata here


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


def reliable_client_creation() -> str:
    """
    Reliably create a client and test topic operations with retry logic.

    Returns:
        str: The full topic name in format "namespace.topic-name"
    """
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            time.sleep(5)

        topic_name = None
        kafka_topic = None
        client = None
        try:
            client = Client()
            client.create_key()
            # key_result = client.create_key()
            # print(f"Key result: {key_result}")
            # # If key is fresh (just created), wait for IAM policy to propagate
            # if key_result.get("fresh", False):
            #     time.sleep(8)

            topic_name = f"topic-{str(uuid.uuid4())[:5]}"
            kafka_topic = f"{client.namespace}.{topic_name}"
            client.create_topic(topic_name)
            time.sleep(3)  # Wait after topic creation before produce

            producer = KafkaProducer(kafka_topic)
            for i in range(3):
                future = producer.send(
                    kafka_topic, {"message_id": i + 1, "content": f"Message {i + 1}"}
                )
                future.get(timeout=30)
            producer.close()

            time.sleep(2)
            consumer = KafkaConsumer(kafka_topic, auto_offset_reset="earliest")
            consumer.poll(timeout_ms=10000)
            consumer.close()

            client.delete_topic(topic_name)
            return kafka_topic
        except Exception as e:
            logger.info(f"Error in attempt {attempt}: {type(e).__name__}: {str(e)}")
            if client:
                try:
                    if topic_name:
                        client.delete_topic(topic_name)
                except Exception:
                    pass
                try:
                    client.delete_user()
                except Exception:
                    pass
            continue
