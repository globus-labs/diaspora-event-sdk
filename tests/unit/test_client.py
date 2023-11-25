import pytest
from unittest.mock import Mock, patch
from unittest.mock import MagicMock
from diaspora_event_sdk import Client


@pytest.fixture
def mock_login_manager():
    login_manager = Mock()
    login_manager.get_web_client.return_value = Mock()
    login_manager.get_auth_client.return_value = Mock(
        oauth2_userinfo=lambda: {"sub": "test_sub"})
    login_manager._token_storage.get_token_data.return_value = {
        'access_key': 'test_access', 'secret_key': 'test_secret'}
    login_manager.get_web_client.return_value.create_key.return_value = {
        "status": "success", "access_key": "new_access", "secret_key": "new_secret"}

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
    client.logout()
    client.login_manager.logout.assert_called_once()


def test_create_key(client):
    result = client.create_key()
    assert result == {"username": "test_sub", "password": "new_secret"}


def test_retrieve_key_existing(client):
    result = client.retrieve_key()
    assert result == {"username": "test_sub", "password": "test_secret"}


def test_retrieve_key_missing(client, mock_login_manager):
    # Set up side_effect for get_token_data: None on first call, token data on the next
    mock_login_manager._token_storage.get_token_data.side_effect = [
        None,  # First call returns None
        {'access_key': 'test_access', 'secret_key': 'test_secret'}
    ]

    # First call to retrieve_key, which should internally call create_key
    result = client.retrieve_key()

    # Assertions to check the expected behavior
    # As create_key generates new_secret
    assert result["password"] == "new_secret"
    assert result["username"] == "test_sub"


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
