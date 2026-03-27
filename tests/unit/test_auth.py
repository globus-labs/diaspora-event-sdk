import os
from unittest import mock

import pytest


class TestGetClientCreds:
    def test_returns_none_when_no_env_vars(self):
        from diaspora_event_sdk.sdk.auth.client_login import get_client_creds

        with mock.patch.dict(os.environ, {}, clear=True):
            client_id, client_secret = get_client_creds()
            assert client_id is None
            assert client_secret is None

    def test_returns_values_when_env_vars_set(self):
        from diaspora_event_sdk.sdk.auth.client_login import get_client_creds

        with mock.patch.dict(
            os.environ,
            {
                "DIASPORA_SDK_CLIENT_ID": "test-id",
                "DIASPORA_SDK_CLIENT_SECRET": "test-secret",  # pragma: allowlist secret
            },
        ):
            client_id, client_secret = get_client_creds()
            assert client_id == "test-id"
            assert client_secret == "test-secret"  # pragma: allowlist secret


class TestGetGlobusApp:
    def test_returns_client_app_with_creds(self):
        from globus_sdk import ClientApp

        from diaspora_event_sdk.sdk.auth.globus_app import get_globus_app

        with mock.patch.dict(
            os.environ,
            {
                "DIASPORA_SDK_CLIENT_ID": "test-id",
                "DIASPORA_SDK_CLIENT_SECRET": "test-secret",  # pragma: allowlist secret
            },
        ):
            app = get_globus_app()
            assert isinstance(app, ClientApp)

    def test_returns_user_app_without_creds(self):
        from globus_sdk import UserApp

        from diaspora_event_sdk.sdk.auth.globus_app import get_globus_app

        env = {k: v for k, v in os.environ.items() if not k.startswith("DIASPORA_SDK_")}
        with mock.patch.dict(os.environ, env, clear=True):
            app = get_globus_app()
            assert isinstance(app, UserApp)

    def test_raises_when_only_secret_set(self):
        from diaspora_event_sdk.sdk.auth.globus_app import get_globus_app

        env = {k: v for k, v in os.environ.items() if k != "DIASPORA_SDK_CLIENT_ID"}
        env["DIASPORA_SDK_CLIENT_SECRET"] = "test-secret"  # pragma: allowlist secret
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Both DIASPORA_SDK_CLIENT_ID"):
                get_globus_app()


class TestClientInit:
    def test_app_and_authorizer_mutually_exclusive(self):
        from unittest.mock import MagicMock

        from diaspora_event_sdk.sdk.client import Client

        mock_app = MagicMock()
        mock_authorizer = MagicMock()

        with pytest.raises(ValueError, match="mutually exclusive"):
            Client(app=mock_app, authorizer=mock_authorizer)
