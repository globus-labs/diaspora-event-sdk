from __future__ import annotations

import logging
import os
import typing as t

import globus_sdk

from ._environments import get_web_service_url
from .auth.globus_app import get_globus_app

logger = logging.getLogger(__name__)


class FilteredClientCredentialsAuthorizer(globus_sdk.ClientCredentialsAuthorizer):
    """ClientCredentialsAuthorizer that handles multi-resource-server token responses.

    Some Globus clients return tokens for multiple resource servers in a single
    client credentials response (e.g., when scopes have dependent scopes).
    The base ClientCredentialsAuthorizer expects exactly one token.

    This subclass filters the response to only the target resource server.
    """

    def __init__(
        self,
        confidential_client: globus_sdk.ConfidentialAppAuthClient,
        scopes: list[str],
        *,
        resource_server: str,
        access_token: str | None = None,
        expires_at: int | None = None,
        on_refresh: t.Callable | None = None,
    ) -> None:
        self._target_resource_server = resource_server
        super().__init__(
            confidential_client=confidential_client,
            scopes=scopes,
            access_token=access_token,
            expires_at=expires_at,
            on_refresh=on_refresh,
        )

    def _extract_token_data(self, res) -> dict[str, t.Any]:
        token_data = res.by_resource_server
        if self._target_resource_server in token_data:
            return token_data[self._target_resource_server]
        # Fall back to default behavior if target not found
        return super()._extract_token_data(res)


class Client:
    DIASPORA_CLIENT_ID = os.getenv(
        "DIASPORA_SDK_CLIENT_ID",
        "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe",
    )
    DIASPORA_SCOPE = os.getenv(
        "DIASPORA_SCOPE",
        "https://auth.globus.org/scopes/2b9d2f5c-fa32-45b5-875b-b24cd343b917/action_all",
    )
    DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"

    def __init__(
        self,
        environment: str | None = None,
        *,
        app: globus_sdk.GlobusApp | None = None,
        authorizer: globus_sdk.authorizers.GlobusAuthorizer | None = None,
        **kwargs,
    ):
        self.web_service_address = get_web_service_url(environment)

        self.app: globus_sdk.GlobusApp | None = None
        self.authorizer: globus_sdk.authorizers.GlobusAuthorizer | None = None

        if app and authorizer:
            raise ValueError("'app' and 'authorizer' are mutually exclusive.")
        elif authorizer:
            self.authorizer = authorizer
            self.web_client = self._make_web_client(authorizer=authorizer)
        else:
            self.app = app if app else get_globus_app(environment=environment)
            if isinstance(self.app, globus_sdk.ClientApp):
                # For client credentials, build a filtered authorizer that
                # handles multi-resource-server token responses
                web_authorizer = self._make_client_creds_authorizer(
                    self.app, self.DIASPORA_RESOURCE_SERVER, [self.DIASPORA_SCOPE]
                )
                self.web_client = self._make_web_client(authorizer=web_authorizer)
            else:
                self.web_client = self._make_web_client(app=self.app)

        # Get user identity
        self._resolve_identity()

    def _make_client_creds_authorizer(
        self,
        app: globus_sdk.ClientApp,
        resource_server: str,
        scopes: list[str],
    ) -> FilteredClientCredentialsAuthorizer:
        """Build a FilteredClientCredentialsAuthorizer for client credentials flow."""
        from .auth.client_login import get_client_creds

        client_id, client_secret = get_client_creds()
        confidential_client = globus_sdk.ConfidentialAppAuthClient(
            client_id=client_id, client_secret=client_secret
        )
        return FilteredClientCredentialsAuthorizer(
            confidential_client=confidential_client,
            scopes=scopes,
            resource_server=resource_server,
        )

    def _resolve_identity(self):
        """Resolve the user's OpenID subject and namespace."""
        if isinstance(self.app, globus_sdk.ClientApp):
            # For client credentials, build a separate filtered authorizer
            # for the auth resource server (openid scope)
            from globus_sdk.scopes import AuthScopes

            auth_authorizer = self._make_client_creds_authorizer(
                self.app, AuthScopes.resource_server, [AuthScopes.openid]
            )
            auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
        elif self.app:
            auth_client = globus_sdk.AuthClient(app=self.app)
        else:
            auth_client = globus_sdk.AuthClient(authorizer=self.authorizer)

        self.subject_openid = auth_client.userinfo()["sub"]
        self.namespace = f"ns-{self.subject_openid.replace('-', '')[-12:]}"

    def _make_web_client(self, **kwargs):
        from .web_client import WebClient

        return WebClient(base_url=self.web_service_address, **kwargs)

    def logout(self):
        """Remove credentials from your local system"""
        if self.authorizer:
            logger.warning(
                "Logout is not supported when using a GlobusAuthorizer. "
                "You must manage your own credentials."
            )
            return
        if self.app:
            self.app.logout()

    def create_user(self):
        """
        Create an IAM user with policy and namespace for the current user (POST /api/v3/user).
        Returns status, message, subject, and namespace.
        """
        resp = self.web_client.create_user(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    def delete_user(self):
        """
        Delete the IAM user and all associated resources for the current user (DELETE /api/v3/user).
        Returns status and message.
        """
        resp = self.web_client.delete_user(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    def create_key(self):
        """
        Create a new access key for the current user (POST /api/v3/key).
        This will replace any existing access key (force refresh).
        Returns status, message, access_key, secret_key, and create_date.
        """
        resp = self.web_client.create_key(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    def delete_key(self):
        """
        Delete access keys from IAM and DynamoDB for the current user (DELETE /api/v3/key).
        Returns status and message.
        """
        resp = self.web_client.delete_key(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    def list_namespaces(self):
        """
        List all namespaces owned by the current user and their topics (GET /api/v3/namespace).
        Returns status, message, and namespaces dict (namespace -> list of topics).
        """
        resp = self.web_client.list_namespaces(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    def create_topic(self, topic: str):
        """
        Create a topic under the user's default namespace (POST /api/v3/{namespace}/{topic}).
        Returns status, message, and topics list.
        """
        resp = self.web_client.create_topic(self.subject_openid, self.namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    def delete_topic(self, topic: str):
        """
        Delete a topic from the user's default namespace (DELETE /api/v3/{namespace}/{topic}).
        Returns status, message, and topics list.
        """
        resp = self.web_client.delete_topic(self.subject_openid, self.namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    def recreate_topic(self, topic: str):
        """
        Recreate a topic in the user's default namespace by deleting and recreating it (PUT /api/v3/{namespace}/{topic}/recreate).
        Returns status and message.
        """
        resp = self.web_client.recreate_topic(
            self.subject_openid, self.namespace, topic
        )
        return resp.data if hasattr(resp, "data") else resp
