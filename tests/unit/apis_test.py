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


def test_create_key(setup, client):
    key_response = client.create_key()
    assert isinstance(key_response, dict)
    assert "access_key" in key_response
    assert "secret_key" in key_response
    assert "endpoint" in key_response


def test_register_topic(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    register_response = client.register_topic(topic)
    assert register_response["status"] in ["success", "no-op"]
    assert "message" in register_response


def test_list_topics(setup, client):
    topics = client.list_topics()
    assert topics["status"] == "success"
    assert isinstance(topics["topics"], list)
    assert len(topics["topics"]) > 0
    expected_topics = ["diaspora-cicd"]
    assert set(expected_topics).issubset(set(topics["topics"]))


def test_get_topic_configs(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    client.register_topic(topic)
    configs_response = client.get_topic_configs(topic)
    assert configs_response["status"] == "success"
    assert "configs" in configs_response
    assert isinstance(configs_response["configs"], dict)


def test_update_topic_configs(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    client.register_topic(topic)
    configs = {"min.insync.replicas": 1}
    update_response = client.update_topic_configs(topic, configs)
    assert update_response["status"] == "success"
    assert "before" in update_response
    assert "after" in update_response
    assert isinstance(update_response["before"], dict)
    assert isinstance(update_response["after"], dict)


def test_update_topic_partitions(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    client.register_topic(topic)
    new_partitions = 2
    partitions_response = client.update_topic_partitions(topic, new_partitions)
    assert partitions_response["status"] in ["success", "error"]
    if partitions_response["status"] == "error":
        assert "message" in partitions_response


def test_reset_topic(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    client.register_topic(topic)
    reset_response = client.reset_topic(topic)
    assert reset_response["status"] in ["success", "error"]
    if reset_response["status"] == "error":
        assert "message" in reset_response


def test_user_access_management(setup, client):
    topic = "topic" + client.subject_openid[-12:]
    client.register_topic(topic)
    user_id = "e2a8169b-feef-4d56-8eba-ab12747bee04"
    grant_response = client.grant_user_access(topic, user_id)
    assert grant_response["status"] in ["success", "no-op"]
    assert "message" in grant_response

    list_users_response = client.list_topic_users(topic)
    assert list_users_response["status"] == "success"
    assert "users" in list_users_response
    assert isinstance(list_users_response["users"], list)

    revoke_response = client.revoke_user_access(topic, user_id)
    assert revoke_response["status"] in ["success", "no-op"]
    assert "message" in revoke_response


if __name__ == "__main__":
    pytest.main(["-s", "tests/unit/test_apis.py"])
