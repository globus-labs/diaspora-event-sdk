# Adapted from globus-compute SDK (Apache 2.0)
# https://github.com/globus/globus-compute/blob/68b1174cc06d4e91f49663128951a0c0080abef9/compute_sdk/globus_compute_sdk/sdk/auth/token_storage.py
from __future__ import annotations

import os

from globus_sdk.token_storage import SQLiteTokenStorage

from .._environments import _get_envname
from .client_login import get_client_creds
from .diaspora_dir import ensure_diaspora_dir


def _get_storage_filepath():
    diaspora_dir = ensure_diaspora_dir()
    return os.path.join(diaspora_dir, "storage.db")


def _resolve_namespace(environment: str | None = None) -> str:
    """Return the namespace used to save tokens. This will check if a
    client login is being used and return either `user/<envname>` or
    `clientprofile/<envname>/<clientid>`.
    """
    env = environment if environment is not None else _get_envname()

    client_id, client_secret = get_client_creds()
    if client_id and client_secret:
        return f"clientprofile/{env}/{client_id}"

    return f"user/{env}"


def get_token_storage(environment: str | None = None) -> SQLiteTokenStorage:
    return SQLiteTokenStorage(
        filepath=_get_storage_filepath(),
        namespace=_resolve_namespace(environment),
        connect_params={"check_same_thread": False},
    )
