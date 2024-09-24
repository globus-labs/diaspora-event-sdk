import json
from typing import Optional

from diaspora_event_sdk.sdk.login_manager import (
    LoginManager,
    LoginManagerProtocol,
    requires_login,
)

from ._environments import DIASPORA_RESOURCE_SERVER, get_web_service_url


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
    def create_key(self):
        """
        Revokes existing keys, generates a new key, and updates the token storage with the newly created key and the Diaspora endpoint.
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
        Retrieves the key from local token storage, and calls create_key() if the local key is not found.
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
        Returns a list of topics currently registered under the user's account.
        """
        return self.web_client.list_topics(self.subject_openid)

    @requires_login
    def register_topic(self, topic):
        """
        Registers a new topic the user's account with permissions to read, write, and describe the topic.
        """
        return self.web_client.register_topic(self.subject_openid, topic, "register")

    @requires_login
    def unregister_topic(self, topic):
        """
        Unregisters a topic from a user's account, but all existing events within the topic are unaffected.
        """
        return self.web_client.register_topic(self.subject_openid, topic, "unregister")

    @requires_login
    def get_topic_configs(self, topic):
        """
        Retrieves the current configurations for a registered topic.
        """
        return self.web_client.get_topic_configs(self.subject_openid, topic)

    @requires_login
    def update_topic_configs(self, topic, configs):
        """
        Updates the configurations for a registered topic.
        """
        return self.web_client.update_topic_configs(self.subject_openid, topic, configs)

    @requires_login
    def update_topic_partitions(self, topic, new_partitions):
        """
        Increases the number of partitions for a given topic to the specified new partition count.
        """
        return self.web_client.update_topic_partitions(
            self.subject_openid, topic, new_partitions
        )

    @requires_login
    def reset_topic(self, topic):
        """
        Deletes and recreates the topic, removing all messages and restoring the topic to the default configurations while user access is not affected.
        """
        return self.web_client.reset_topic(self.subject_openid, topic)

    @requires_login
    def grant_user_access(self, topic, user):
        """
        Authorizes another user to access a registered topic under the invoker's account.
        """
        return self.web_client.grant_user_access(
            self.subject_openid, topic, user, "grant"
        )

    @requires_login
    def revoke_user_access(self, topic, user):
        """
        Removes access permissions for another user from a registered topic under the invoker's account.
        """
        return self.web_client.grant_user_access(
            self.subject_openid, topic, user, "revoke"
        )

    @requires_login
    def list_topic_users(self, topic):
        """
        Returns a list of users that have access to the topic.
        """
        return self.web_client.list_topic_users(self.subject_openid, topic)

    @requires_login
    def list_triggers(self):
        """
        Retrieves a list of triggers associated created under the user's account, showing each trigger's configurations and UUID.
        """
        return self.web_client.list_triggers(self.subject_openid)

    @requires_login
    def create_trigger(self, topic, function, function_configs, trigger_configs):
        """
        Creates a new trigger under the user's account with specific function and invocation configurations.
        """
        return self.web_client.create_trigger(
            self.subject_openid,
            topic,
            function,
            "create",
            function_configs,
            trigger_configs,
        )

    @requires_login
    def delete_trigger(self, topic, function):
        """
        Deletes a trigger and related AWS resources, while the associated topic remains unaffected.
        """
        return self.web_client.create_trigger(
            self.subject_openid, topic, function, "delete", {}, {}
        )

    @requires_login
    def update_trigger(self, trigger_uuid, trigger_configs):
        """
        Updates invocation configurations of an existing trigger, identified by its unique trigger UUID.
        """
        return self.web_client.update_trigger(
            self.subject_openid, trigger_uuid, trigger_configs
        )

    @requires_login
    def list_log_streams(self, trigger):
        """
        List log streams of a trigger under the user's account
        """
        return self.web_client.list_log_streams(self.subject_openid, trigger)

    @requires_login
    def get_log_events(self, trigger, stream):
        """
        Get events in a particular log stream of a trigger under the user's account
        """
        return self.web_client.get_log_events(self.subject_openid, trigger, stream)
