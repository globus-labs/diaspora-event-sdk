import json
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
