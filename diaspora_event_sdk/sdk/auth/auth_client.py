from __future__ import annotations

from globus_sdk import AuthClient
from globus_sdk.scopes import AuthScopes


class DiasporaAuthClient(AuthClient):
    default_scope_requirements = [
        AuthScopes.openid,
    ]
