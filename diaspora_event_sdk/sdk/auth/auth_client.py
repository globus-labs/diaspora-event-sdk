# Adapted from globus-compute SDK (Apache 2.0)
# https://github.com/globus/globus-compute/blob/68b1174cc06d4e91f49663128951a0c0080abef9/compute_sdk/globus_compute_sdk/sdk/auth/auth_client.py
from __future__ import annotations

from globus_sdk import AuthClient
from globus_sdk.scopes import AuthScopes


class DiasporaAuthClient(AuthClient):
    default_scope_requirements = [
        AuthScopes.openid,
    ]
