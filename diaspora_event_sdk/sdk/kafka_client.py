import json

from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic

from .client import Client
from ._environments import MSK_SCRAM_ENDPOINT


class KafkaAdminClient(KafkaAdminClient):
    def __init__(self, globusClient: Client):
        keys = globusClient.retrieve_or_create_key()
        super().__init__(
            bootstrap_servers=MSK_SCRAM_ENDPOINT,
            security_protocol="SASL_SSL",
            sasl_mechanism="SCRAM-SHA-512",
            sasl_plain_username=keys["username"],
            sasl_plain_password=keys["secret_key"],
            api_version=(3, 5, 1),
        )


class Producer(KafkaProducer):
    def __init__(self, **configs):
        keys = Client().retrieve_or_create_key()
        if "bootstrap_servers" not in configs:
            configs['bootstrap_servers'] = MSK_SCRAM_ENDPOINT
        if "security_protocol" not in configs:
            configs['security_protocol'] = "SASL_SSL"
        if "sasl_mechanism" not in configs:
            configs['sasl_mechanism'] = "SCRAM-SHA-512"
        if "sasl_plain_username" not in configs:
            configs['sasl_plain_username'] = keys["username"]
        if "sasl_plain_password" not in configs:
            configs['sasl_plain_password'] = keys["secret_key"]
        if "api_version" not in configs:
            configs['api_version'] = (3, 5, 1)
        if "value_serializer" not in configs:
            configs['value_serializer'] = lambda v: json.dumps(
                v).encode('utf-8')
        super().__init__(**configs)


class Consumer(KafkaConsumer):
    def __init__(self, *topics, **configs):
        keys = Client().retrieve_or_create_key()
        if "bootstrap_servers" not in configs:
            configs['bootstrap_servers'] = MSK_SCRAM_ENDPOINT
        if "security_protocol" not in configs:
            configs['security_protocol'] = "SASL_SSL"
        if "sasl_mechanism" not in configs:
            configs['sasl_mechanism'] = "SCRAM-SHA-512"
        if "sasl_plain_username" not in configs:
            configs['sasl_plain_username'] = keys["username"]
        if "sasl_plain_password" not in configs:
            configs['sasl_plain_password'] = keys["secret_key"]
        if "api_version" not in configs:
            configs['api_version'] = (3, 5, 1)
        super().__init__(*topics, **configs)
