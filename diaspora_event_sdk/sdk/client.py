import json

from diaspora_event_sdk.sdk.login_manager.manager import LoginManager
from diaspora_event_sdk.sdk.login_manager import requires_login
from globus_compute_sdk.sdk.login_manager import LoginManagerProtocol

from ._environments import TOKEN_EXCHANGE, DIASPORA_RESOURCE_SERVER


class Client:

    def __init__(
        self,
        environment: str | None = None,
        login_manager: LoginManagerProtocol | None = None,
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
            base_url=TOKEN_EXCHANGE
        )
        self.auth_client = self.login_manager.get_auth_client()
        self.subject_openid = self.auth_client.oauth2_userinfo()["sub"]

    def logout(self):
        """Remove credentials from your local system"""
        self.login_manager.logout()

    @requires_login
    def create_key(self):
        resp = self.web_client.create_key(self.subject_openid)
        if resp["status"] == "error":
            raise Exception("should not happen")

        tokens = self.login_manager._token_storage.get_token_data(
            DIASPORA_RESOURCE_SERVER)
        tokens['access_key'], tokens['secret_key'] = resp['access_key'], resp['secret_key']
        with self.login_manager._access_lock:
            self.login_manager._token_storage._connection.executemany(
                "REPLACE INTO token_storage(namespace, resource_server, token_data_json) "
                "VALUES(?, ?, ?)",
                [
                    (self.login_manager._token_storage.namespace,
                     DIASPORA_RESOURCE_SERVER,
                     json.dumps(tokens))
                ],
            )
            self.login_manager._token_storage._connection.commit()
        return resp

    @requires_login
    def retrieve_or_create_key(self):
        tokens = self.login_manager._token_storage.get_token_data(
            DIASPORA_RESOURCE_SERVER)
        if "access_key" in tokens and "secret_key" in tokens:
            return {
                "status": "succeed", "username": self.subject_openid,
                "access_key": tokens['access_key'],
                "secret_key": tokens['secret_key']
            }
        return self.create_key()

    @requires_login
    def acl_list(self):
        return self.web_client.acl_list(self.subject_openid)

    @requires_login
    def acl_add(self, topic):
        return self.web_client.acl_add(self.subject_openid, topic)

    @requires_login
    def acl_remove(self, topic):
        return self.web_client.acl_remove(self.subject_openid, topic)
