import json
from typing import Optional

from diaspora_event_sdk.sdk.login_manager import (
    LoginManager,
    LoginManagerProtocol,
    requires_login,
)

from ._environments import DIASPORA_RESOURCE_SERVER, TOKEN_EXCHANGE


class Client:
    def __init__(
        self,
        environment: Optional[str] = None,
        login_manager: Optional[LoginManagerProtocol] = None,
    ):
        # if a login manager was passed, no login flow is triggered
        if login_manager is not None:
            self.login_manager: LoginManagerProtocol = login_manager
        # but if login handling is implicit (as when no login manager is passed)
        # then ensure that the user is logged in
        else:
            self.login_manager = LoginManager(environment=environment)
            self.login_manager.ensure_logged_in()

        self.web_client = self.login_manager.get_web_client(
            base_url=TOKEN_EXCHANGE)
        self.auth_client = self.login_manager.get_auth_client()
        self.subject_openid = self.auth_client.oauth2_userinfo()["sub"]

    def logout(self):
        """Remove credentials from your local system"""
        self.login_manager.logout()

    @requires_login
    def create_key(self):
        """
        Invalidate previous keys (if any) and generate a new one
        """
        resp = self.web_client.create_key(self.subject_openid)
        if resp["status"] == "error":
            raise Exception("should not happen")
        tokens = self.login_manager._token_storage.get_token_data(
            DIASPORA_RESOURCE_SERVER
        )
        tokens["access_key"] = resp["access_key"]
        tokens["secret_key"] = resp["secret_key"]
        tokens["endpoint"] = resp["endpoint"]
        with self.login_manager._access_lock:
            self.login_manager._token_storage._connection.executemany(
                "REPLACE INTO token_storage(namespace, resource_server, token_data_json) "
                "VALUES(?, ?, ?)",
                [
                    (
                        self.login_manager._token_storage.namespace,
                        DIASPORA_RESOURCE_SERVER,
                        json.dumps(tokens),
                    )
                ],
            )
            self.login_manager._token_storage._connection.commit()
        return {
            "access_key": tokens["access_key"],
            "secret_key": tokens["secret_key"],
            "endpoint": tokens["endpoint"],
        }

    @requires_login
    def retrieve_key(self):
        """
        Attempt to retrieve the key from local token storage, and call create_key if local key is not found
        """
        tokens = self.login_manager._token_storage.get_token_data(
            DIASPORA_RESOURCE_SERVER
        )
        if (
            tokens is None
            or "endpoint" not in tokens
            or "access_key" not in tokens
            or "secret_key" not in tokens
        ):
            return self.create_key()
        else:
            return {
                "access_key": tokens["access_key"],
                "secret_key": tokens["secret_key"],
                "endpoint": tokens["endpoint"],
            }

    @requires_login
    def put_secret_key(self, access_key, secret_key, endpoint):
        tokens = self.login_manager._token_storage.get_token_data(
            DIASPORA_RESOURCE_SERVER
        )
        tokens["access_key"] = access_key
        tokens["secret_key"] = secret_key
        tokens["endpoint"] = endpoint
        with self.login_manager._access_lock:
            self.login_manager._token_storage._connection.executemany(
                "REPLACE INTO token_storage(namespace, resource_server, token_data_json) "
                "VALUES(?, ?, ?)",
                [
                    (
                        self.login_manager._token_storage.namespace,
                        DIASPORA_RESOURCE_SERVER,
                        json.dumps(tokens),
                    )
                ],
            )
            self.login_manager._token_storage._connection.commit()

    @requires_login
    def list_topics(self):
        """
        Retrieves the list of topics associated with the user's OpenID.
        """
        return self.web_client.list_topics(self.subject_openid)

    @requires_login
    def register_topic(self, topic):
        """
        Registers a new topic under the user's OpenID.
        """
        return self.web_client.register_topic(self.subject_openid, topic, "register")

    @requires_login
    def unregister_topic(self, topic):
        """
        Unregisters a topic from the user's OpenID.
        """
        return self.web_client.register_topic(self.subject_openid, topic, "unregister")

    @requires_login
    def get_topic_configs(self, topic):
        """
        Get topic configurations.
        """
        return self.web_client.get_topic_configs(self.subject_openid, topic)

    @requires_login
    def update_topic_configs(self, topic, configs):
        """
        Set topic configurations.
        """
        return self.web_client.update_topic_configs(self.subject_openid, topic, configs)

    @requires_login
    def update_topic_partitions(self, topic, new_partitions):
        """
        Adjust topic number of partitions
        """
        return self.web_client.update_topic_partitions(self.subject_openid, topic, new_partitions)

    @requires_login
    def grant_user_access(self, topic, user):
        """
        Registers a new topic under the user's OpenID.
        """
        return self.web_client.grant_user_access(self.subject_openid, topic, user, "grant")

    @requires_login
    def revoke_user_access(self, topic, user):
        """
        Unregisters a topic from the user's OpenID.
        """
        return self.web_client.grant_user_access(self.subject_openid, topic, user, "revoke")

    @requires_login
    def list_triggers(self):
        """
        Retrieves the list of functions associated with the user's OpenID.
        """
        return self.web_client.list_triggers(self.subject_openid)

    @requires_login
    def create_trigger(self, topic, function, function_configs):
        """
        Registers a new functions under the user's OpenID.
        """
        return self.web_client.create_trigger(self.subject_openid, topic, function, "create", function_configs)

    @requires_login
    def delete_trigger(self, topic, function):
        """
        Unregisters a functions from the user's OpenID.
        """
        return self.web_client.create_trigger(self.subject_openid, topic, function, "delete", {})

    @requires_login
    def update_trigger(self, trigger_uuid, trigger_configs):
        """
        Update a functions's trigger'.
        """
        return self.web_client.update_trigger(self.subject_openid, trigger_uuid, trigger_configs)
