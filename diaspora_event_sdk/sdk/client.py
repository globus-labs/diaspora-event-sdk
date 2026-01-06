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
    def create_key_v3(self):
        """
        Create a new access key for the current user (POST /api/v3/key).
        This will replace any existing access key.
        Returns the access key, secret key, create_date, and endpoint.
        """
        resp = self.web_client.create_key_v3(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def retrieve_key_v3(self):
        """
        Retrieve a key from DynamoDB if it exists, or create a new one if not (GET /api/v3/key).
        Returns the access key, secret key, create_date, endpoint, and retrieved_from_dynamodb flag.
        """
        resp = self.web_client.retrieve_key_v3(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_key_v3(self):
        """
        Delete access keys from IAM and DynamoDB for the current user (DELETE /api/v3/key).
        Returns status and message.
        """
        resp = self.web_client.delete_key_v3(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def list_topics_v3(self):
        """
        List topics for the current user.
        Returns a list of topics the user has access to.
        """
        resp = self.web_client.list_topics_v3(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def register_topic_v3(self, topic: str):
        """
        Register a topic for the current user.
        Returns status and message.
        """
        resp = self.web_client.register_topic_v3(self.subject_openid, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def unregister_topic_v3(self, topic: str):
        """
        Unregister a topic for the current user.
        Returns status and message.
        """
        resp = self.web_client.unregister_topic_v3(self.subject_openid, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def create_namespace_v3(self, namespace: str):
        """
        Create a namespace for the current user (POST /api/v3/namespace).
        Returns status, message, and namespaces list.
        """
        resp = self.web_client.create_namespace_v3(self.subject_openid, namespace)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def list_namespaces_v3(self):
        """
        List all namespaces owned by the current user and their topics (GET /api/v3/namespace).
        Returns status, message, and namespaces dict (namespace -> list of topics).
        """
        resp = self.web_client.list_namespaces_v3(self.subject_openid)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_namespace_v3(self, namespace: str):
        """
        Delete a namespace for the current user (DELETE /api/v3/namespace).
        Returns status, message, and remaining namespaces list.
        """
        resp = self.web_client.delete_namespace_v3(self.subject_openid, namespace)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def create_topic_v3(self, namespace: str, topic: str):
        """
        Create a topic under a namespace (POST /api/v3/{namespace}/{topic}).
        Returns status, message, namespace, and topic.
        """
        resp = self.web_client.create_topic_v3(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def delete_topic_v3(self, namespace: str, topic: str):
        """
        Delete a topic from a namespace (DELETE /api/v3/{namespace}/{topic}).
        Returns status, message, namespace, and topic.
        """
        resp = self.web_client.delete_topic_v3(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

    @requires_login
    def recreate_topic_v3(self, namespace: str, topic: str):
        """
        Recreate a topic by deleting and recreating it via KafkaAdminClient (PUT /api/v3/{namespace}/{topic}/recreate).
        Returns status, message, namespace, and topic.
        """
        resp = self.web_client.recreate_topic_v3(self.subject_openid, namespace, topic)
        return resp.data if hasattr(resp, "data") else resp

