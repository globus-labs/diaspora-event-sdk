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
            keys = client.retrieve_key_v3()
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
    
    This function:
    1. Creates a namespace using the last 12 characters of the user's UUID
    2. Creates a topic with a unique name
    3. Creates a new access key
    4. Verifies the topic works by producing and consuming messages
    5. Retries from the beginning if any step fails
    
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
        try:
            # Create client
            client = Client()
            namespace = f"ns-{client.subject_openid.replace('-', '')[-12:]}"
            
            # Create namespace
            print(client.create_namespace_v3(namespace))
            
            # Create topic with random name
            topic_name = f"topic-{str(uuid.uuid4())[:5]}"
            msg = client.create_topic_v3(namespace, topic_name)
            print(msg)
            if msg.get("status") != "success":
                try:
                    client.delete_topic_v3(namespace, topic_name)
                except Exception:
                    pass
                continue
            
            kafka_topic = f"{namespace}.{topic_name}"
            
            # Create key
            print(client.create_key_v3())
            time.sleep(8)
            
            # Create producer
            producer_ok = False
            producer = None
            for retry in range(5):
                if retry > 0:
                    time.sleep(8)
                try:
                    producer = KafkaProducer(kafka_topic)
                    producer.send(kafka_topic, {"test": "message"}).get(timeout=30)
                    producer.close()
                    producer_ok = True
                    break
                except Exception as e:
                    error_msg = f"Producer error (attempt {retry + 1}/5): {type(e).__name__}: {str(e)}"
                    logger.info(error_msg)
                    print(error_msg)
                    try:
                        if producer:
                            producer.close()
                    except Exception:
                        pass
                    if isinstance(e, (TopicAuthorizationFailedError, KafkaTimeoutError)) and retry < 4:
                        continue
                    try:
                        client.delete_topic_v3(namespace, topic_name)
                    except Exception:
                        pass
                    if not isinstance(e, (TopicAuthorizationFailedError, KafkaTimeoutError)):
                        break
            
            if not producer_ok:
                continue
            
            # Create consumer
            consumer_ok = False
            consumer = None
            for retry in range(5):
                if retry > 0:
                    time.sleep(3)
                try:
                    consumer = KafkaConsumer(kafka_topic, auto_offset_reset="earliest")
                    consumer.poll(timeout_ms=10000)
                    consumer.close()
                    consumer_ok = True
                    break
                except Exception as e:
                    error_msg = f"Consumer error (attempt {retry + 1}/5): {type(e).__name__}: {str(e)}"
                    logger.info(error_msg)
                    print(error_msg)
                    try:
                        if consumer:
                            consumer.close()
                    except Exception:
                        pass
                    if isinstance(e, (TopicAuthorizationFailedError, KafkaTimeoutError)) and retry < 4:
                        continue
                    try:
                        client.delete_topic_v3(namespace, topic_name)
                    except Exception:
                        pass
                    if not isinstance(e, (TopicAuthorizationFailedError, KafkaTimeoutError)):
                        break
            
            if not consumer_ok:
                continue
            
            logger.info(f"reliable_topic_creation completed successfully in {attempt} attempt(s), topic: {kafka_topic}")
            return kafka_topic
        except Exception as e:
            logger.info(f"Unexpected error in attempt {attempt}: {type(e).__name__}: {str(e)}")
            if topic_name:
                try:
                    client.delete_topic_v3(namespace, topic_name)
                except Exception:
                    pass
            continue


def reliable_topic_deletion(kafka_topic: str) -> dict:
    """
    Delete a topic without deleting the namespace.
    
    Args:
        kafka_topic: Full topic name in format "namespace.topic-name"
    
    Returns:
        dict: Result from delete_topic_v3 API call
    
    Raises:
        ValueError: If kafka_topic is not in the correct format
        Exception: If topic deletion fails
    """
    # Parse namespace and topic from kafka_topic
    if "." not in kafka_topic:
        raise ValueError(f"kafka_topic must be in format 'namespace.topic-name', got: {kafka_topic}")
    
    namespace, topic_name = kafka_topic.split(".", 1)
    
    # Create client and delete topic
    client = Client()
    result = client.delete_topic_v3(namespace, topic_name)
    
    # Log the results
    logger.info(f"reliable_topic_deletion result: {result}")
    
    return result
