from typing import Optional

from diaspora_event_sdk.sdk.login_manager import (
    LoginManager,
    LoginManagerProtocol,
    requires_login,
)

from ._environments import get_web_service_url


class Client:
    def __init__(
        self,
        environment: Optional[str] = None,
        login_manager: Optional[LoginManagerProtocol] = None,
    ):
        self.web_service_address = get_web_service_url(environment)

        # if a login manager was passed, no login flow is triggered
        if login_manager is not None:
            self.login_manager: LoginManagerProtocol = login_manager
        # but if login handling is implicit (as when no login manager is passed)
        # then ensure that the user is logged in
        else:
            self.login_manager = LoginManager(environment=environment)
            self.login_manager.ensure_logged_in()

        self.web_client = self.login_manager.get_web_client(
            base_url=self.web_service_address
        )
        self.auth_client = self.login_manager.get_auth_client()
        self.subject_openid = self.auth_client.userinfo()["sub"]

    def logout(self):
        """Remove credentials from your local system"""
        self.login_manager.logout()

    @requires_login
    def create_user(self):
        """
        Create an IAM user with policy and namespace for the current user (POST /api/v3/user).
        Returns status, message, subject, and namespace.
        """
        resp = self.web_client.create_user(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_user(self):
        """
        Delete the IAM user and all associated resources for the current user (DELETE /api/v3/user).
        Returns status and message.
        """
        resp = self.web_client.delete_user(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def create_key(self):
        """
        Create a new access key for the current user (POST /api/v3/key).
        This will replace any existing access key (force refresh).
        Returns status, message, access_key, secret_key, and create_date.
        """
        resp = self.web_client.create_key(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def get_key(self):
        """
        Retrieve a key from DynamoDB if it exists, or create a new one if not (GET /api/v3/key).
        Returns status, message, access_key, secret_key, and create_date.
        """
        resp = self.web_client.retrieve_key(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_key(self):
        """
        Delete access keys from IAM and DynamoDB for the current user (DELETE /api/v3/key).
        Returns status and message.
        """
        resp = self.web_client.delete_key(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def list_namespaces(self):
        """
        List all namespaces owned by the current user and their topics (GET /api/v3/namespace).
        Returns status, message, and namespaces dict (namespace -> list of topics).
        """
        resp = self.web_client.list_namespaces(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def create_topic(self, namespace: str, topic: str):
        """
        Create a topic under a namespace (POST /api/v3/{namespace}/{topic}).
        Returns status, message, and topics list.
        """
        resp = self.web_client.create_topic(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_topic(self, namespace: str, topic: str):
        """
        Delete a topic from a namespace (DELETE /api/v3/{namespace}/{topic}).
        Returns status, message, and topics list.
        """
        resp = self.web_client.delete_topic(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def recreate_topic(self, namespace: str, topic: str):
        """
        Recreate a topic by deleting and recreating it (PUT /api/v3/{namespace}/{topic}/recreate).
        Returns status and message.
        """
        resp = self.web_client.recreate_topic(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp
