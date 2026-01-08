import pytest
from unittest.mock import Mock
from unittest.mock import MagicMock
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.web_client import WebClient
from diaspora_event_sdk.sdk.login_manager import LoginManager


@pytest.fixture
def mock_login_manager():
    """Create a mock login manager for testing."""
    login_manager = Mock(spec=LoginManager())
    login_manager.get_web_client.return_value = Mock(spec=WebClient)
    login_manager.get_auth_client.return_value = Mock(
        userinfo=lambda: {"sub": "test_sub"}
    )
    login_manager._token_storage.get_token_data.return_value = {
        "username": "test_sub",
        "access_key": "test_access",
        "secret_key": "test_secret",  # pragma: allowlist secret
        "endpoint": "test_endpoint",
    }
    login_manager.get_web_client.return_value.create_key.return_value = {
        "status": "success",
        "username": "test_sub",
        "access_key": "new_access",
        "secret_key": "new_secret",  # pragma: allowlist secret
        "endpoint": "new_endpoint",
    }

    # Use MagicMock for _access_lock
    login_manager._access_lock = MagicMock()

    return login_manager


@pytest.fixture
def client(mock_login_manager):
    """Create a Client instance with mocked login manager."""
    return Client(login_manager=mock_login_manager)


def test_init(mock_login_manager):
    """Test Client initialization."""
    client = Client(login_manager=mock_login_manager)
    assert client.login_manager == mock_login_manager


def test_logout(client):
    """Test logout functionality."""
    assert not client.login_manager.logout.called, "Verify test setup"
    client.logout()
    assert client.login_manager.logout.called
