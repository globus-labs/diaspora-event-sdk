from __future__ import annotations

import os

import globus_sdk
from globus_sdk import Scope

from diaspora_event_sdk.sdk.utils.uuid_like import UUID_LIKE_T

from ._environments import get_web_service_url

DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"
DIASPORA_SCOPE = os.getenv(
    "DIASPORA_SCOPE",
    f"https://auth.globus.org/scopes/{DIASPORA_RESOURCE_SERVER}/action_all",
)


class WebClient(globus_sdk.BaseClient):
    resource_server = DIASPORA_RESOURCE_SERVER
    default_scope_requirements = [Scope(DIASPORA_SCOPE)]

    def __init__(
        self,
        *,
        environment: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        if base_url is None:
            base_url = get_web_service_url(environment)

        super().__init__(environment=environment, base_url=base_url, **kwargs)

    def create_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_user endpoint (POST /api/v3/user)."""
        return self.post("/api/v3/user", headers={"Subject": str(subject)})

    def delete_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_user endpoint (DELETE /api/v3/user)."""
        return self.delete("/api/v3/user", headers={"Subject": str(subject)})

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_key endpoint (POST /api/v3/key)."""
        return self.post("/api/v3/key", headers={"Subject": str(subject)})

    def delete_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_key endpoint (DELETE /api/v3/key)."""
        return self.delete("/api/v3/key", headers={"Subject": str(subject)})

    def list_namespaces(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 list_namespaces endpoint (GET /api/v3/namespace)."""
        return self.get("/api/v3/namespace", headers={"Subject": str(subject)})

    def create_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_topic endpoint (POST /api/v3/{namespace}/{topic})."""
        return self.post(
            f"/api/v3/{namespace}/{topic}", headers={"Subject": str(subject)}
        )

    def delete_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_topic endpoint (DELETE /api/v3/{namespace}/{topic})."""
        return self.delete(
            f"/api/v3/{namespace}/{topic}", headers={"Subject": str(subject)}
        )

    def recreate_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 recreate_topic endpoint (PUT /api/v3/{namespace}/{topic}/recreate)."""
        return self.put(
            f"/api/v3/{namespace}/{topic}/recreate",
            headers={"Subject": str(subject)},
        )
