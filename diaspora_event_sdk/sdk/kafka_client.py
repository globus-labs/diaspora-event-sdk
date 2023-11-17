import json

from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic

from .client import Client
from ._environments import MSK_SCRAM_ENDPOINT

DEFAULT_CONFIGS = {
    "bootstrap_servers":  MSK_SCRAM_ENDPOINT,
    "security_protocol": "SASL_SSL",
    "sasl_mechanism": "SCRAM-SHA-512",
    "api_version": (3, 5, 1)
}


class KafkaAdmin(KafkaAdminClient):
    def __init__(self, **configs):
        keys = Client().retrieve_or_create_key()
        conf = DEFAULT_CONFIGS.copy()
        conf["sasl_plain_username"] = keys["username"]
        conf["sasl_plain_password"] = keys["secret_key"]
        conf.update(configs)
        super().__init__(**conf)


class Producer(KafkaProducer):
    def __init__(self, **configs):
        keys = Client().retrieve_or_create_key()
        conf = DEFAULT_CONFIGS.copy()
        conf["sasl_plain_username"] = keys["username"]
        conf["sasl_plain_password"] = keys["secret_key"]
        conf["value_serializer"] = lambda v: json.dumps(
            v).encode('utf-8')
        conf.update(configs)
        super().__init__(**conf)


class Consumer(KafkaConsumer):
    def __init__(self, *topics, **configs):
        keys = Client().retrieve_or_create_key()
        conf = DEFAULT_CONFIGS.copy()
        conf["sasl_plain_username"] = keys["username"]
        conf["sasl_plain_password"] = keys["secret_key"]
        conf.update(configs)
        super().__init__(*topics, **conf)
