import os
from diaspora_logger import GlobusAuthTokenProvider
from kafka import KafkaConsumer


def run_consumer_example(topic, group_id):
    # Obtain the refresh token from the environment variable
    refresh_token = os.getenv('DIASPORA_REFRESH')

    if not refresh_token:
        raise ValueError("Environment variable DIASPORA_REFRESH not set")

    bootstrap_servers = ["52.200.217.146:9093"]
    security_protocol = "SASL_PLAINTEXT"
    sasl_mechanism = "OAUTHBEARER"
    provider = GlobusAuthTokenProvider(refresh_token)
    consumer = KafkaConsumer(topic,
                             group_id=group_id,
                             bootstrap_servers=bootstrap_servers,
                             security_protocol=security_protocol,
                             sasl_mechanism=sasl_mechanism,
                             sasl_oauth_token_provider=provider,
                             api_version=(3, 5, 1))
    for msg in consumer:
        print(msg)
