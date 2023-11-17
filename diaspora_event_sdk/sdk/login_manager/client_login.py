"""
Logic for using client identities with the Diaspora Event SDK

This is based on the Globus CLI client login:
https://github.com/globus/globus-cli/blob/main/src/globus_cli/login_manager/client_login.py
"""
from __future__ import annotations

import logging
import os
import uuid

import globus_sdk

log = logging.getLogger(__name__)


def _get_client_creds_from_env() -> tuple[str | None, str | None]:
    client_id = os.getenv("DIASPORA_SDK_CLIENT_ID")
    client_secret = os.getenv("DIASPORA_SDK_CLIENT_SECRET")
    return client_id, client_secret


def is_client_login() -> bool:
    """
    Return True if the correct env variables have been set to use a
    client identity with the Diaspora Event SDK
    """
    client_id, client_secret = _get_client_creds_from_env()

    if bool(client_id) ^ bool(client_secret):
        raise ValueError(
            "Both DIASPORA_SDK_CLIENT_ID and DIASPORA_SDK_CLIENT_SECRET must "
            "be set to use a client identity. Either set both environment "
            "variables, or unset them to use a normal login."
        )

    return bool(client_id) and bool(client_secret)


def get_client_login() -> globus_sdk.ConfidentialAppAuthClient:
    """
    Return the ConfidentialAppAuthClient for the client identity
    logged into the SDK
    """
    if not is_client_login():
        raise ValueError("No client is logged in")

    client_id, client_secret = _get_client_creds_from_env()

    try:
        uuid.UUID(client_id)
    except ValueError:
        log.warning(
            "VERY LIKELY INVALID CLIENT ID (did you copy the username and not the id?)"
            f"\n  Received: '{client_id}'"
        )
    return globus_sdk.ConfidentialAppAuthClient(
        client_id=str(client_id),
        client_secret=str(client_secret),
    )
