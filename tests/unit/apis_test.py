import pytest
import os
import logging
from globus_sdk import ConfidentialAppAuthClient
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.login_manager import tokenstore

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup():
    client_id = os.environ["DIASPORA_SDK_CLIENT_ID"]
    client_secret = os.environ["DIASPORA_SDK_CLIENT_SECRET"]
    requested_scopes = os.environ["CLIENT_SCOPE"]
    # assert client_id
    # assert client_secret
    # assert requested_scopes

    ca = ConfidentialAppAuthClient(
        client_id=client_id,
        client_secret=client_secret,
    )
    token_response = ca.oauth2_client_credentials_tokens(
        requested_scopes=requested_scopes,
    )
    token = token_response.by_resource_server[client_id]

    storage = tokenstore.get_token_storage_adapter()
    storage.store(token_response)
    storage.get_by_resource_server()

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "requested_scopes": requested_scopes,
        "token_response": token_response,
        "token": token,
    }


@pytest.fixture(scope="module")
def client():
    return Client()
