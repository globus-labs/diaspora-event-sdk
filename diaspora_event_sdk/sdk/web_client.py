from typing import Optional

import globus_sdk

from diaspora_event_sdk.sdk.utils.uuid_like import UUID_LIKE_T

from ._environments import get_web_service_url


class WebClient(globus_sdk.BaseClient):
    def __init__(
        self,
        *,
        environment: Optional[str] = None,
        base_url: Optional[str] = None,
        app_name: Optional[str] = None,
        **kwargs,
    ):
        if base_url is None:
            base_url = get_web_service_url(environment)

        super().__init__(environment=environment, base_url=base_url, **kwargs)

        self._user_app_name = None
        self.user_app_name = app_name

    def create_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_user endpoint (POST /api/v3/user)."""
        return self.post("/api/v3/user", headers={"Subject": str(subject)})

    def delete_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_user endpoint (DELETE /api/v3/user)."""
        return self.delete("/api/v3/user", headers={"Subject": str(subject)})

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_key endpoint (POST /api/v3/key)."""
        return self.post("/api/v3/key", headers={"Subject": str(subject)})

    def retrieve_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 get_key endpoint (GET /api/v3/key)."""
        return self.get("/api/v3/key", headers={"Subject": str(subject)})

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
