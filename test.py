import dill

from globus_sdk.services.auth.response.oauth import OAuthTokenResponse
from diaspora_event_sdk.sdk.login_manager import LoginManager
from diaspora_event_sdk.sdk.login_manager.login_flow import do_link_auth_flow


class TestLoginManager(LoginManager):
    def run_login_flow(self, *, scopes: list[str] | None = None):
        if scopes is None:  # flatten scopes to list of strings if none provided
            scopes = [
                s for _rs_name, rs_scopes in self.login_requirements for s in rs_scopes
            ]

        token = do_link_auth_flow(scopes)
        with open("token_response.dill", "wb") as f:
            dill.dump(token, f)
        with self._access_lock:
            self._token_storage.store(token)


if __name__ == '__main__':
    tlm = TestLoginManager()
    # tlm.run_login_flow()

    # with open("token_response.dill", 'rb') as file:
    #     token = dill.load(file)
    # with tlm._access_lock:
    #     tlm._token_storage.store(token)
