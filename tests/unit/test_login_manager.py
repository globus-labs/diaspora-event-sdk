import dill
import pytest
from unittest.mock import Mock, patch
from unittest.mock import MagicMock
from diaspora_event_sdk import Client
from diaspora_event_sdk .sdk.login_manager import LoginManager

@pytest.fixture
def mock_login_manager():
    # Create a mock LoginManager and configure its behavior
    mock = Mock(spec=LoginManager)

    # Define the side effect for the mocked run_login_flow
    def custom_run_login_flow():
        with open("token_response.dill", 'rb') as file:
            token = dill.load(file)
            print(token)
        with mock._access_lock:
            mock._token_storage.store(token)

    # Assign the side effect to the mock run_login_flow method
    mock.run_login_flow.side_effect = custom_run_login_flow

    return mock

@pytest.fixture
def mock_auth_client():
    mock = Mock()
    with open("token_response.dill", 'rb') as file:
        token = dill.load(file)
        sub = token.decode_id_token()['sub']
        mock.oauth2_userinfo.return_value = {"sub":sub}
    return mock

@pytest.fixture
def client(mock_login_manager: Mock):
    return Client(login_manager=mock_login_manager)

def test_init(mock_login_manager: Mock, mock_auth_client: Mock):
    # Configure the mock login manager to return the mock auth client
    mock_login_manager.get_auth_client.return_value = mock_auth_client

    # Create an instance of Client with the mock login manager
    client = Client(login_manager=mock_login_manager)

    # Verify that the mock auth client's oauth2_userinfo method was called
    mock_auth_client.oauth2_userinfo.assert_called_once()
    userinfo_result = mock_auth_client.oauth2_userinfo.return_value
    assert userinfo_result['sub'].endswith("ab12747bee03")

    result = client.create_key()

    # Assert that the create_key method returns the expected result
    expected_result = {"username": "user123", "password": "secret456"}
    assert result == expected_result