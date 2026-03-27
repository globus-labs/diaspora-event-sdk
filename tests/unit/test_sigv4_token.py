"""Test vendored botocore SigV4 signing produces valid MSK auth tokens.

These tests validate the token structure without needing a real Kafka cluster.
Since we vendor botocore instead of depending on it, this catches vendoring regressions.
"""

import base64
from urllib.parse import parse_qs, urlparse

import pytest

from diaspora_event_sdk.sdk.aws_iam_msk import generate_auth_token
from diaspora_event_sdk.sdk.botocore.credentials import Credentials


class TestSigV4TokenStructure:
    """Validate the structure of generated MSK auth tokens."""

    @pytest.fixture
    def set_fake_aws_creds(self, monkeypatch):
        monkeypatch.setenv("OCTOPUS_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("OCTOPUS_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    def test_token_is_valid_base64(self, set_fake_aws_creds):
        token, expiry_ms = generate_auth_token("us-east-1")
        # Re-add padding and decode
        padded = token + "=" * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        assert decoded.startswith("https://kafka.us-east-1.amazonaws.com/")

    def test_token_contains_required_sigv4_params(self, set_fake_aws_creds):
        token, _ = generate_auth_token("us-east-1")
        padded = token + "=" * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        parsed = urlparse(decoded)
        params = parse_qs(parsed.query)

        assert params["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
        assert "X-Amz-Credential" in params
        assert "X-Amz-Date" in params
        assert params["X-Amz-Expires"] == ["900"]
        assert params["X-Amz-SignedHeaders"] == ["host"]
        assert "X-Amz-Signature" in params

        # Credential should contain the access key and kafka-cluster service
        cred = params["X-Amz-Credential"][0]
        assert cred.startswith("AKIAIOSFODNN7EXAMPLE/")
        assert "us-east-1/kafka-cluster/aws4_request" in cred

    def test_token_contains_action_param(self, set_fake_aws_creds):
        token, _ = generate_auth_token("us-east-1")
        padded = token + "=" * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        parsed = urlparse(decoded)
        params = parse_qs(parsed.query)

        assert params["Action"] == ["kafka-cluster:Connect"]

    def test_token_contains_user_agent(self, set_fake_aws_creds):
        token, _ = generate_auth_token("us-east-1")
        padded = token + "=" * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        assert "User-Agent=" in decoded

    def test_expiry_is_positive_milliseconds(self, set_fake_aws_creds):
        _, expiry_ms = generate_auth_token("us-east-1")
        assert isinstance(expiry_ms, int)
        assert expiry_ms > 0
        # Should be roughly current time + 900s (15min), in ms
        import time
        now_ms = int(time.time() * 1000)
        assert abs(expiry_ms - (now_ms + 900_000)) < 5_000  # within 5s tolerance

    def test_different_regions_produce_different_endpoints(self, set_fake_aws_creds):
        token_east, _ = generate_auth_token("us-east-1")
        token_west, _ = generate_auth_token("us-west-2")

        def decode(t):
            padded = t + "=" * (4 - len(t) % 4)
            return base64.urlsafe_b64decode(padded).decode("utf-8")

        assert "kafka.us-east-1.amazonaws.com" in decode(token_east)
        assert "kafka.us-west-2.amazonaws.com" in decode(token_west)

    def test_missing_credentials_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("OCTOPUS_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("OCTOPUS_AWS_SECRET_ACCESS_KEY", raising=False)
        with pytest.raises(ValueError, match="must be set"):
            generate_auth_token("us-east-1")


class TestCredentials:
    """Validate vendored Credentials class matches upstream behavior."""

    def test_credentials_basic(self):
        creds = Credentials("access", "secret")
        assert creds.access_key == "access"
        assert creds.secret_key == "secret"
        assert creds.token is None
        assert creds.account_id is None
        assert creds.method == "explicit"

    def test_credentials_with_token_and_account_id(self):
        creds = Credentials("access", "secret", token="tok", account_id="123")
        assert creds.token == "tok"
        assert creds.account_id == "123"

    def test_frozen_credentials(self):
        creds = Credentials("access", "secret", token="tok", account_id="123")
        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == "access"
        assert frozen.secret_key == "secret"
        assert frozen.token == "tok"
        assert frozen.account_id == "123"
