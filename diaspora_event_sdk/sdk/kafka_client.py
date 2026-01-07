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


def reliable_topic_creation() -> str:
    """
    Reliably create a topic with retry logic for handling failures.

    This function in a while loop:
    1. Calls create_key to ensure access keys are available
    2. Calls list_namespaces to get an existing namespace (or uses default)
    3. Creates a random topic under the namespace
    4. Creates a producer to test producing messages
    5. Creates a consumer to test consuming from the topic
    6. Returns the topic name if all work out
    7. Otherwise retries from the beginning

    Returns:
        str: The full topic name in format "namespace.topic-name"

    Raises:
        Exception: If topic creation fails after retries or if client cannot be created.
    """
    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            time.sleep(5)

        topic_name = None
        kafka_topic = None
        namespace = None
        client = None
        try:
            # Create client
            # os.environ["DIASPORA_SDK_ENVIRONMENT"] = "local"
            client = Client()

            # Create key
            print(f"Creating key (attempt {attempt})...")
            key_result = client.create_key()
            print(f"Key creation: {key_result}")
            time.sleep(8)  # Wait for IAM policy to propagate

            # Get namespaces
            print(f"Listing namespaces (attempt {attempt})...")
            namespaces_result = client.list_namespaces()
            print(f"Namespaces: {namespaces_result}")

            if namespaces_result.get("status") != "success":
                logger.info(f"Failed to list namespaces: {namespaces_result}")
                continue

            # Get first namespace or use default
            namespaces = namespaces_result.get("namespaces", {})
            if not namespaces:
                # No namespaces found, user needs to create one first
                logger.info("No namespaces found. User must create a namespace first.")
                raise RuntimeError(
                    "No namespaces found. Please create a namespace first using create_user() or create_namespace()."
                )

            # Use the first namespace
            namespace = list(namespaces.keys())[0]
            print(f"Using namespace: {namespace}")

            # Create topic with random name
            topic_name = f"topic-{str(uuid.uuid4())[:5]}"
            print(f"Creating topic {topic_name} under namespace {namespace}...")
            topic_result = client.create_topic(namespace, topic_name)
            print(f"Topic creation: {topic_result}")

            if topic_result.get("status") != "success":
                logger.info(f"Failed to create topic: {topic_result}")
                continue

            kafka_topic = f"{namespace}.{topic_name}"

            # Wait a bit for topic to be fully created
            time.sleep(3)

            # Create producer and test produce
            print(f"Testing producer for topic {kafka_topic}...")
            producer_ok = False
            producer = None
            try:
                producer = KafkaProducer(kafka_topic)
                future = producer.send(kafka_topic, {"test": "message"})
                result = future.get(timeout=30)
                producer.close()
                print(f"Producer test successful: offset={result.offset}")
                producer_ok = True
            except Exception as e:
                error_msg = f"Producer error: {type(e).__name__}: {str(e)}"
                logger.info(error_msg)
                print(error_msg)
                try:
                    if producer:
                        producer.close()
                except Exception:
                    pass
                try:
                    client.delete_topic(namespace, topic_name)
                except Exception:
                    pass
                continue

            if not producer_ok:
                continue

            # Wait a bit after producer test before testing consumer
            time.sleep(3)

            # Create consumer and test consume
            print(f"Testing consumer for topic {kafka_topic}...")
            consumer_ok = False
            consumer = None
            try:
                consumer = KafkaConsumer(kafka_topic, auto_offset_reset="earliest")
                messages = consumer.poll(timeout_ms=10000)
                consumer.close()
                print(
                    f"Consumer test successful: polled {len(messages)} message batches"
                )
                consumer_ok = True
            except Exception as e:
                error_msg = f"Consumer error: {type(e).__name__}: {str(e)}"
                logger.info(error_msg)
                print(error_msg)
                try:
                    if consumer:
                        consumer.close()
                except Exception:
                    pass
                try:
                    client.delete_topic(namespace, topic_name)
                except Exception:
                    pass
                continue

            if not consumer_ok:
                continue

            logger.info(
                f"reliable_topic_creation completed successfully in {attempt} attempt(s), topic: {kafka_topic}"
            )
            print(f"Successfully created and verified topic: {kafka_topic}")
            return kafka_topic
        except Exception as e:
            error_msg = (
                f"Unexpected error in attempt {attempt}: {type(e).__name__}: {str(e)}"
            )
            logger.info(error_msg)
            print(error_msg)
            if topic_name and namespace and client:
                try:
                    client.delete_topic(namespace, topic_name)
                except Exception:
                    pass
            # Re-raise if it's a non-retryable error (like no namespaces)
            if isinstance(e, RuntimeError):
                raise
            continue


def reliable_topic_deletion(kafka_topic: str) -> dict:
    """
    Delete a topic without deleting the namespace.

    Args:
        kafka_topic: Full topic name in format "namespace.topic-name"

    Returns:
        dict: Result from delete_topic API call

    Raises:
        ValueError: If kafka_topic is not in the correct format
        Exception: If topic deletion fails
    """
    # Parse namespace and topic from kafka_topic
    if "." not in kafka_topic:
        raise ValueError(
            f"kafka_topic must be in format 'namespace.topic-name', got: {kafka_topic}"
        )

    namespace, topic_name = kafka_topic.split(".", 1)

    # Create client and delete topic
    client = Client()
    result = client.delete_topic(namespace, topic_name)

    # Log the results
    logger.info(f"reliable_topic_deletion result: {result}")

    return result
