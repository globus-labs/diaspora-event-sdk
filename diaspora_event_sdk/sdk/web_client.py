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

    def create_user_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """
        Call the v3 create_user endpoint (POST /api/v3/user).
        Creates an IAM user with policy and namespace for the user.
        Note: This endpoint requires both Subject and Authorization headers.
        The Authorization header is automatically added by the BaseClient's authorizer.
        """
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.post("/api/v3/user", headers=headers)

    def delete_user_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """
        Call the v3 delete_user endpoint (DELETE /api/v3/user).
        Deletes the IAM user and all associated resources.
        Note: This endpoint requires both Subject and Authorization headers.
        The Authorization header is automatically added by the BaseClient's authorizer.
        """
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.delete("/api/v3/user", headers=headers)

    def create_key_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """
        Call the v3 create_key endpoint (POST /api/v3/key).
        Creates a new access key for the user, replacing any existing key.
        Note: This endpoint requires both Subject and Authorization headers.
        The Authorization header is automatically added by the BaseClient's authorizer.
        """
        # The BaseClient will automatically add Authorization header via authorizer
        # We also explicitly set it in headers to ensure it's passed correctly
        headers = {"Subject": str(subject)}

        # Get access token from authorizer if available
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    # Extract token if it's in "Bearer <token>" format
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                # If we can't get it from authorizer, BaseClient will handle it
                pass

        return self.post("/api/v3/key", headers=headers)

    def retrieve_key_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """
        Call the v3 get_key endpoint (GET /api/v3/key).
        Retrieves key from DynamoDB if exists, or creates a new one if not.
        Note: This endpoint requires both Subject and Authorization headers.
        The Authorization header is automatically added by the BaseClient's authorizer.
        """
        # The BaseClient will automatically add Authorization header via authorizer
        # We also explicitly set it in headers to ensure it's passed correctly
        headers = {"Subject": str(subject)}

        # Get access token from authorizer if available
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    # Extract token if it's in "Bearer <token>" format
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                # If we can't get it from authorizer, BaseClient will handle it
                pass

        return self.get("/api/v3/key", headers=headers)

    def delete_key_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """
        Call the v3 delete_key endpoint (DELETE /api/v3/key).
        Deletes access keys from IAM and DynamoDB for the user.
        Note: This endpoint requires both Subject and Authorization headers.
        The Authorization header is automatically added by the BaseClient's authorizer.
        """
        # The BaseClient will automatically add Authorization header via authorizer
        # We also explicitly set it in headers to ensure it's passed correctly
        headers = {"Subject": str(subject)}

        # Get access token from authorizer if available
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    # Extract token if it's in "Bearer <token>" format
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                # If we can't get it from authorizer, BaseClient will handle it
                pass

        return self.delete("/api/v3/key", headers=headers)

    def list_namespaces_v3(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 list_namespaces endpoint (GET /api/v3/namespace)."""
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.get("/api/v3/namespace", headers=headers)

    def create_topic_v3(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_topic endpoint (POST /api/v3/{namespace}/{topic})."""
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.post(f"/api/v3/{namespace}/{topic}", headers=headers)

    def delete_topic_v3(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_topic endpoint (DELETE /api/v3/{namespace}/{topic})."""
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.delete(f"/api/v3/{namespace}/{topic}", headers=headers)

    def recreate_topic_v3(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 recreate_topic endpoint (PUT /api/v3/{namespace}/{topic}/recreate)."""
        headers = {"Subject": str(subject)}
        if hasattr(self, "authorizer") and self.authorizer is not None:
            try:
                auth_header = self.authorizer.get_authorization_header()
                if auth_header:
                    if auth_header.startswith("Bearer "):
                        headers["Authorization"] = auth_header
                    else:
                        headers["Authorization"] = f"Bearer {auth_header}"
            except Exception:
                pass
        return self.put(f"/api/v3/{namespace}/{topic}/recreate", headers=headers)
