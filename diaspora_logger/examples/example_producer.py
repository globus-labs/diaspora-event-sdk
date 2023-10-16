import os
from diaspora_logger import DiasporaLogger


def on_send_success(record_metadata):
    print(
        f'Message sent to {record_metadata.topic}:{record_metadata.partition} {record_metadata.offset}')


def run_producer_example(topic):
    # Read the refresh token from the environment variable
    refresh_token = os.getenv('DIASPORA_REFRESH')

    if not refresh_token:
        raise ValueError("Environment variable DIASPORA_REFRESH not set")

    kafka_logger = DiasporaLogger(
        topic=topic,
        bootstrap_servers=["52.200.217.146:9093"],
        refresh_token=refresh_token,
    )

    kafka_logger.send_sync({'message': 'Synchronous message'})
    kafka_logger.send_async(
        {'message': 'Asynchronous message'}, callback=on_send_success)
