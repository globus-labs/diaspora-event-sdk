import pytest
import os
import logging
from globus_sdk import ConfidentialAppAuthClient
from diaspora_event_sdk import Client
from diaspora_event_sdk.sdk.login_manager import tokenstore
from diaspora_event_sdk.sdk._environments import get_web_service_url


# os.environ['DIASPORA_SDK_ENVIRONMENT'] = 'local'

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup():
    client_id = os.environ["DIASPORA_SDK_CLIENT_ID"]
    client_secret = os.environ["DIASPORA_SDK_CLIENT_SECRET"]
    requested_scopes = os.environ["CLIENT_SCOPE"]


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

    logger.info(get_web_service_url())
    logger.info(f"Client ID: {client_id}")
    logger.info(f"Client Secret: {client_secret}")
    logger.info(f"Requested Scopes: {requested_scopes}")
    logger.info(f"Token Response: {token_response}")

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


def test_create_key(setup, client):
    # Call the create_key method
    key_response = client.create_key()

    # Log the key response
    logger.info(f"Key Response: {key_response}")

    # Assert the expected outcome
    assert isinstance(key_response, dict), "The response should be a dictionary"
    assert "access_key" in key_response, "The response should contain an access_key"
    assert "secret_key" in key_response, "The response should contain a secret_key"
    assert "endpoint" in key_response, "The response should contain an endpoint"


def test_register_topic(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Register the topic
    register_response = client.register_topic(topic)

    # Log the registration response
    logger.info(f"Registration Response: {register_response}")

    # Assert the expected outcome
    assert register_response["status"] in [
        "success",
        "no-op",
    ], "The status should be either success or no-op"
    assert "message" in register_response, "The response should contain a message"

    # Print the response (optional)
    print(register_response)


def test_list_topics(setup, client):
    # Call the list_topics method
    topics = client.list_topics()

    # Log the topics
    logger.info(f"Topics: {topics}")

    # Assert the expected outcome (this will vary depending on the expected result)
    assert topics["status"] == "success", "The status should be success"
    assert isinstance(topics["topics"], list), "The topics should be a list"
    assert len(topics["topics"]) > 0, "The list should not be empty"

    # Optionally, assert the contents of the list if you know what to expect
    expected_topics = ["diaspora-cicd"]  # Replace with actual expected topics
    assert set(expected_topics).issubset(
        set(topics["topics"])
    ), "The topics should include the expected topics"


def test_get_topic_configs(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Ensure the topic is registered
    client.register_topic(topic)

    # Get the topic configurations
    configs_response = client.get_topic_configs(topic)

    # Log the configurations response
    logger.info(f"Configurations Response: {configs_response}")

    # Assert the expected outcome
    assert configs_response["status"] == "success", "The status should be success"
    assert "configs" in configs_response, "The response should contain configs"
    assert isinstance(
        configs_response["configs"], dict
    ), "Configs should be a dictionary"

    # Print the response (optional)
    print(configs_response)


def test_update_topic_configs(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Ensure the topic is registered
    client.register_topic(topic)

    # Define the new configurations
    configs = {"min.insync.replicas": 1}

    # Update the topic configurations
    update_response = client.update_topic_configs(topic, configs)

    # Log the update response
    logger.info(f"Update Response: {update_response}")

    # Assert the expected outcome
    assert update_response["status"] == "success", "The status should be success"
    assert "before" in update_response, "The response should contain 'before' configs"
    assert "after" in update_response, "The response should contain 'after' configs"
    assert isinstance(
        update_response["before"], dict
    ), "'before' should be a dictionary"
    assert isinstance(update_response["after"], dict), "'after' should be a dictionary"

    # Print the response (optional)
    print(update_response)


def test_update_topic_partitions(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Ensure the topic is registered
    client.register_topic(topic)

    # Increase the number of partitions
    new_partitions = 2
    partitions_response = client.update_topic_partitions(topic, new_partitions)

    # Log the partitions response
    logger.info(f"Partitions Response: {partitions_response}")

    # Assert the expected outcome
    assert partitions_response["status"] in [
        "success",
        "error",
    ], "The status should be either success or error"
    if partitions_response["status"] == "error":
        assert (
            "message" in partitions_response
        ), "The error response should contain a message"

    # Print the response (optional)
    print(partitions_response)


def test_reset_topic(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Ensure the topic is registered
    client.register_topic(topic)

    # Reset the topic
    reset_response = client.reset_topic(topic)

    # Log the reset response
    logger.info(f"Reset Response: {reset_response}")

    # Assert the expected outcome
    assert reset_response["status"] in [
        "success",
        "error",
    ], "The status should be either success or error"
    if reset_response["status"] == "error":
        assert (
            "message" in reset_response
        ), "The error response should contain a message"

    # Print the response (optional)
    print(reset_response)


def test_user_access_management(setup, client):
    # Generate a unique topic name
    topic = "topic" + client.subject_openid[-12:]

    # Ensure the topic is registered
    client.register_topic(topic)

    # Authorize another user to access the topic
    user_id = "e2a8169b-feef-4d56-8eba-ab12747bee04"
    grant_response = client.grant_user_access(topic, user_id)

    # Log the grant response
    logger.info(f"Grant Response: {grant_response}")

    # # Assert the expected outcome for granting access
    assert grant_response["status"] in [
        "success",
        "no-op",
    ], "The status should be either success or no-op"
    assert "message" in grant_response, "The response should contain a message"

    # Print the grant response (optional)
    print(grant_response)

    # List users that have access to the topic
    list_users_response = client.list_topic_users(topic)

    # Log the list users response
    logger.info(f"List Users Response: {list_users_response}")

    # Assert the expected outcome for listing users
    assert list_users_response["status"] == "success", "The status should be success"
    assert "users" in list_users_response, "The response should contain users"
    assert isinstance(list_users_response["users"], list), "Users should be a list"

    # Print the list users response (optional)
    print(list_users_response)

    # Revoke user access to the topic
    revoke_response = client.revoke_user_access(topic, user_id)

    # Log the revoke response
    logger.info(f"Revoke Response: {revoke_response}")

    # Assert the expected outcome for revoking access
    assert revoke_response["status"] in [
        "success",
        "no-op",
    ], "The status should be either success or no-op"
    assert "message" in revoke_response, "The response should contain a message"

    # Print the revoke response (optional)
    print(revoke_response)


if __name__ == "__main__":
    pytest.main(["-s", "tests/unit/test_apis.py"])
