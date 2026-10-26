"""Diaspora Event Fabric: Resilience-enabling services for science from HPC to edge."""

from diaspora_event_sdk.version import __version__ as _version

__author__ = "The Diaspora Event Team"
__version__ = _version

from diaspora_event_sdk.sdk.auth.globus_app import DEFAULT_CLIENT_ID, get_globus_app
from diaspora_event_sdk.sdk.client import Client
from diaspora_event_sdk.sdk.kafka_client import (
    KafkaConsumer,
    KafkaProducer,
    reliable_client_creation,
)
from diaspora_event_sdk.sdk.rest_consumer import RESTConsumer
from diaspora_event_sdk.sdk.web_client import WebAPIError

__all__ = (
    "DEFAULT_CLIENT_ID",
    "Client",
    "KafkaConsumer",
    "KafkaProducer",
    "RESTConsumer",
    "WebAPIError",
    "get_globus_app",
    "reliable_client_creation",
)
