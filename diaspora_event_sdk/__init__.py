"""Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge."""

from diaspora_event_sdk.version import __version__ as _version

__author__ = "The Diaspora Event Team"
__version__ = _version

from diaspora_event_sdk.sdk.auth.globus_app import get_globus_app
from diaspora_event_sdk.sdk.client import Client
from diaspora_event_sdk.sdk.kafka_client import (
    KafkaConsumer,
    KafkaProducer,
    reliable_client_creation,
)

__all__ = (
    "Client",
    "KafkaProducer",
    "KafkaConsumer",
    "get_globus_app",
    "reliable_client_creation",
)
