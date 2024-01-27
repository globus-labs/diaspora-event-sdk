import pytest
from unittest.mock import Mock
from unittest.mock import MagicMock
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.web_client import WebClient
from diaspora_event_sdk.sdk.login_manager import LoginManager


@pytest.fixture
def mock_login_manager():  # TODO
    login_manager = Mock(spec=LoginManager())
    login_manager.get_web_client.return_value = Mock(spec=WebClient)
    login_manager.get_auth_client.return_value = Mock(
        oauth2_userinfo=lambda: {"sub": "test_sub"}
    )
    login_manager._token_storage.get_token_data.return_value = {
        "username": "test_sub",
        "access_key": "test_access",
        "secret_key": "test_secret",
        "endpoint": "test_endpoint",
    }
    login_manager.get_web_client.return_value.create_key.return_value = {
        "status": "success",
        "username": "test_sub",
        "access_key": "new_access",
        "secret_key": "new_secret",
        "endpoint": "new_endpoint",
    }

    # Use MagicMock for _access_lock
    login_manager._access_lock = MagicMock()

    return login_manager


@pytest.fixture
def client(mock_login_manager):
    return Client(login_manager=mock_login_manager)


def test_init(mock_login_manager):
    client = Client(login_manager=mock_login_manager)
    assert client.login_manager == mock_login_manager


def test_logout(client):
    assert not client.login_manager.logout.called, "Verify test setup"
    client.logout()
    assert client.login_manager.logout.called


def test_create_key(client):
    result = client.create_key()
    assert result == {
        "access_key": "new_access",
        "secret_key": "new_secret",
        "endpoint": "new_endpoint",
    }


def test_retrieve_key_existing(client):
    result = client.retrieve_key()
    assert result == {
        "access_key": "test_access",
        "secret_key": "test_secret",
        "endpoint": "test_endpoint",
    }


def test_retrieve_key_missing(client, mock_login_manager):
    # Set up side_effect for get_token_data: None on first call, token data on the next
    # the second call returns scope, resource_server, access_token, refresh_token, etc.
    mock_login_manager._token_storage.get_token_data.side_effect = [
        None,
        {"scope": "scope", "resource_server": "resource_server"},
    ]

    # should internally call create_key
    result = client.retrieve_key()

    assert result["access_key"] == "new_access"
    assert result["secret_key"] == "new_secret"
    assert result["endpoint"] == "new_endpoint"


def test_list_topics(client):
    client.list_topics()
    client.web_client.list_topics.assert_called_with("test_sub")


def test_register_topic(client):
    topic = "test_topic"
    client.register_topic(topic)
    client.web_client.register_topic.assert_called_with("test_sub", topic)


def test_unregister_topic(client):
    topic = "test_topic"
    client.unregister_topic(topic)
    client.web_client.unregister_topic.assert_called_with("test_sub", topic)
