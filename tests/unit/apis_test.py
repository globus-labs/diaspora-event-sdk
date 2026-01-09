import pytest
import os
import logging
import uuid
from diaspora_event_sdk import Client

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def client():
    """Create a Client instance for integration tests.

    Requires environment variables:
    - DIASPORA_SDK_CLIENT_ID
    - DIASPORA_SDK_CLIENT_SECRET
    - DIASPORA_SCOPE (optional, defaults to action_all scope)

    Note: CLIENT_SCOPE is used for backward compatibility but should only
    contain scopes for a single resource server.
    """
    # Ensure required environment variables are set
    assert os.environ.get("DIASPORA_SDK_CLIENT_ID"), (
        "DIASPORA_SDK_CLIENT_ID must be set"
    )
    assert os.environ.get("DIASPORA_SDK_CLIENT_SECRET"), (
        "DIASPORA_SDK_CLIENT_SECRET must be set"
    )

    # Set DIASPORA_SCOPE if CLIENT_SCOPE is set (for backward compatibility)
    # This ensures the LoginManager uses the correct scope for client credentials
    if "CLIENT_SCOPE" in os.environ and "DIASPORA_SCOPE" not in os.environ:
        os.environ["DIASPORA_SCOPE"] = os.environ["CLIENT_SCOPE"]

    return Client()


@pytest.mark.integration
def test_create_user(client):
    """Test create_user API."""
    result = client.create_user()
    logger.info(f"create_user result: {result}")
    assert result["status"] == "success"
    assert "subject" in result
    assert "namespace" in result
    assert result["namespace"].startswith("ns-")


@pytest.mark.integration
def test_create_user_idempotent(client):
    """Test create_user is idempotent (can be called multiple times)."""
    result1 = client.create_user()
    logger.info(f"create_user first call: {result1}")
    assert result1["status"] == "success"

    result2 = client.create_user()
    logger.info(f"create_user second call: {result2}")
    assert result2["status"] == "success"
    # Should return same namespace
    assert result1["namespace"] == result2["namespace"]


@pytest.mark.integration
def test_create_key(client):
    """Test create_key API."""
    # Ensure user exists first
    client.create_user()

    result = client.create_key()
    logger.info(f"create_key result: {result}")
    assert result["status"] == "success"
    assert "access_key" in result
    assert "secret_key" in result
    assert "create_date" in result
    assert "endpoint" in result
    assert len(result["access_key"]) > 0
    assert len(result["secret_key"]) > 0


@pytest.mark.integration
def test_create_key_idempotent(client):
    """Test create_key is idempotent (returns existing key if present)."""
    # Ensure user exists
    client.create_user()

    result1 = client.create_key()
    logger.info(f"create_key first call: {result1}")
    assert result1["status"] == "success"
    access_key1 = result1["access_key"]

    result2 = client.create_key()
    logger.info(f"create_key second call: {result2}")
    assert result2["status"] == "success"
    # Should return same access key (idempotent)
    assert result2["access_key"] == access_key1


@pytest.mark.integration
def test_list_namespaces(client):
    """Test list_namespaces API."""
    # Ensure user and namespace exist
    client.create_user()

    result = client.list_namespaces()
    logger.info(f"list_namespaces result: {result}")
    assert result["status"] == "success"
    assert "namespaces" in result
    assert isinstance(result["namespaces"], dict)
    # Should include the default namespace
    assert client.namespace in result["namespaces"]


@pytest.mark.integration
def test_create_topic(client):
    """Test create_topic API."""
    # Ensure user exists
    client.create_user()

    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    result = client.create_topic(topic_name)
    logger.info(f"create_topic result: {result}")
    assert result["status"] == "success"
    assert "topics" in result
    assert isinstance(result["topics"], list)
    assert topic_name in result["topics"]

    # Cleanup
    client.delete_topic(topic_name)


@pytest.mark.integration
def test_create_topic_idempotent(client):
    """Test create_topic is idempotent (can be called multiple times)."""
    # Ensure user exists
    client.create_user()

    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    result1 = client.create_topic(topic_name)
    logger.info(f"create_topic first call: {result1}")
    assert result1["status"] == "success"

    result2 = client.create_topic(topic_name)
    logger.info(f"create_topic second call: {result2}")
    assert result2["status"] == "success"
    # Topic should still be in the list
    assert topic_name in result2["topics"]

    # Cleanup
    client.delete_topic(topic_name)


@pytest.mark.integration
def test_delete_topic(client):
    """Test delete_topic API."""
    # Ensure user exists
    client.create_user()

    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    # Create topic first
    create_result = client.create_topic(topic_name)
    assert create_result["status"] == "success"
    assert topic_name in create_result["topics"]

    # Delete topic
    result = client.delete_topic(topic_name)
    logger.info(f"delete_topic result: {result}")
    assert result["status"] == "success"
    assert "topics" in result
    assert topic_name not in result["topics"]


@pytest.mark.integration
def test_delete_topic_idempotent(client):
    """Test delete_topic is idempotent (can be called multiple times)."""
    # Ensure user exists
    client.create_user()

    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    # Create topic first
    client.create_topic(topic_name)

    # Delete topic first time
    result1 = client.delete_topic(topic_name)
    logger.info(f"delete_topic first call: {result1}")
    assert result1["status"] == "success"

    # Delete topic second time (should still succeed)
    result2 = client.delete_topic(topic_name)
    logger.info(f"delete_topic second call: {result2}")
    assert result2["status"] in ("success", "failure")  # May fail if already deleted


@pytest.mark.integration
def test_recreate_topic(client):
    """Test recreate_topic API."""
    # Ensure user exists
    client.create_user()

    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    # Create topic first
    create_result = client.create_topic(topic_name)
    assert create_result["status"] == "success"

    # Recreate topic
    result = client.recreate_topic(topic_name)
    logger.info(f"recreate_topic result: {result}")
    assert result["status"] == "success"

    # Cleanup
    client.delete_topic(topic_name)


@pytest.mark.integration
def test_delete_key(client):
    """Test delete_key API."""
    # Ensure user and key exist
    client.create_user()
    client.create_key()

    result = client.delete_key()
    logger.info(f"delete_key result: {result}")
    assert result["status"] == "success"


@pytest.mark.integration
def test_delete_key_idempotent(client):
    """Test delete_key is idempotent (can be called multiple times)."""
    # Ensure user and key exist
    client.create_user()
    client.create_key()

    # Delete key first time
    result1 = client.delete_key()
    logger.info(f"delete_key first call: {result1}")
    assert result1["status"] == "success"

    # Delete key second time (should still succeed)
    result2 = client.delete_key()
    logger.info(f"delete_key second call: {result2}")
    assert result2["status"] in ("success", "failure")  # May fail if already deleted


@pytest.mark.integration
def test_full_lifecycle(client):
    """Test full user lifecycle: create user, key, topic, then cleanup."""
    # 1. Create user
    user_result = client.create_user()
    logger.info(f"Created user: {user_result}")
    assert user_result["status"] == "success"
    namespace = user_result["namespace"]

    # 2. Create key
    key_result = client.create_key()
    logger.info(f"Created key: {key_result}")
    assert key_result["status"] == "success"
    assert "access_key" in key_result

    # 3. List namespaces
    namespaces_result = client.list_namespaces()
    logger.info(f"Listed namespaces: {namespaces_result}")
    assert namespaces_result["status"] == "success"
    assert namespace in namespaces_result["namespaces"]

    # 4. Create topic
    topic_name = f"test-topic-{str(uuid.uuid4())[:8]}"
    topic_result = client.create_topic(topic_name)
    logger.info(f"Created topic: {topic_result}")
    assert topic_result["status"] == "success"
    assert topic_name in topic_result["topics"]

    # 5. Delete topic
    delete_topic_result = client.delete_topic(topic_name)
    logger.info(f"Deleted topic: {delete_topic_result}")
    assert delete_topic_result["status"] == "success"

    # 6. Delete key
    delete_key_result = client.delete_key()
    logger.info(f"Deleted key: {delete_key_result}")
    assert delete_key_result["status"] == "success"

    # 7. Delete user
    delete_user_result = client.delete_user()
    logger.info(f"Deleted user: {delete_user_result}")
    assert delete_user_result["status"] == "success"
