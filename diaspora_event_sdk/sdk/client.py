from __future__ import annotations

import logging
import os

import globus_sdk

from ._environments import get_web_service_url
from .auth.auth_client import DiasporaAuthClient
from .auth.globus_app import get_globus_app

logger = logging.getLogger(__name__)


class Client:
    DIASPORA_CLIENT_ID = os.getenv(
        "DIASPORA_SDK_CLIENT_ID",
        "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe",
    )
    DIASPORA_SCOPE = os.getenv(
        "DIASPORA_SCOPE",
        "https://auth.globus.org/scopes/2b9d2f5c-fa32-45b5-875b-b24cd343b917/action_all",
    )

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
            self.web_client = self._make_web_client(app=self.app)

        # Get user identity
        if self.app:
            auth_client = DiasporaAuthClient(app=self.app)
        else:
            auth_client = DiasporaAuthClient(authorizer=authorizer)
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
