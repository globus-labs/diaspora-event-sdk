import json
from typing import Dict, Any
import warnings

from ._environments import MSK_SCRAM_ENDPOINT
from .client import Client

# If kafka-python is not installed, Kafka functionality is not available through diaspora-event-sdk.
kafka_available = True
try:
    from kafka import KafkaProducer as KProd  # type: ignore[import-not-found]
    from kafka import KafkaConsumer as KCons  # type: ignore[import-not-found]

except ImportError:
    kafka_available = False


def get_diaspora_config(extra_configs: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Retrieve default Diaspora event fabric connection configurations for Kafka clients.
    Merges default configurations with custom ones provided.
    """
    try:
        keys = Client().retrieve_key()
    except Exception as e:
        raise RuntimeError("Failed to retrieve Kafka keys") from e

    conf = {
        "bootstrap_servers": MSK_SCRAM_ENDPOINT,
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "SCRAM-SHA-512",
        "api_version": (3, 5, 1),
        "sasl_plain_username": keys["username"],
        "sasl_plain_password": keys["password"],
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
                "KafkaProducer is not available. Initialization is a no-op.", RuntimeWarning)

    class KafkaConsumer:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            warnings.warn(
                "KafkaConsumer is not available. Initialization is a no-op.", RuntimeWarning)
