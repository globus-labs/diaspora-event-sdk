import pytest
import os
import logging
from globus_sdk import ConfidentialAppAuthClient
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.login_manager import tokenstore

# Configure module-level logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.fixture(scope='module')
def setup():
    client_id = os.environ['DIASPORA_SDK_CLIENT_ID'] 
    client_secret = os.environ['DIASPORA_SDK_CLIENT_SECRET']
    requested_scopes = os.environ['CLIENT_SCOPE']
    
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
    
    logger.info(f"Client ID: {client_id}")
    logger.info(f"Client Secret: {client_secret}")
    logger.info(f"Requested Scopes: {requested_scopes}")
    logger.info(f"Token Response: {token_response}")
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "requested_scopes": requested_scopes,
        "token_response": token_response,
        "token": token
    }

def test_list_topics(setup):
    # Initialize the client
    c = Client()
    
    # Call the list_topics method
    topics = c.list_topics()
    
    # Log the topics
    logger.info(f"Topics: {topics}")
    
    # Assert the expected outcome (this will vary depending on the expected result)
    assert topics["status"] == "success", "The status should be success"
    assert isinstance(topics["topics"], list), "The topics should be a list"
    assert len(topics["topics"]) > 0, "The list should not be empty"
    
    # Optionally, assert the contents of the list if you know what to expect
    expected_topics = ["diaspora-cicd"]  # Replace with actual expected topics
    assert set(expected_topics).issubset(set(topics["topics"])), "The topics should include the expected topics"

if __name__ == "__main__":
    pytest.main(["-s", "tests/unit/test_apis.py"])
