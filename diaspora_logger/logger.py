# Content of logger.py
import json
import urllib.parse
import http.client
from kafka import KafkaProducer
from kafka.oauth.abstract import AbstractTokenProvider
import logging

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s:%(name)s:%(message)s'
# )

# Create a named logger
logger = logging.getLogger('diaspora')


class GlobusAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, refresh_token, **config):
        super().__init__(**config)
        self.refresh_token = refresh_token

    def post_to_globus(self, refresh_token):
        conn = http.client.HTTPSConnection("auth.globus.org")
        params = urllib.parse.urlencode({
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe",
        })
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/v2/oauth2/token", params, headers)

        response = conn.getresponse()
        response_body = response.read().decode()
        conn.close()

        if response.status == 200:
            return json.loads(response_body)
        else:
            print(f"Failed to retrieve token: {response_body}")
            return None

    def token(self):
        token = self.post_to_globus(self.refresh_token)
        logger.info("client-side new token generated:")
        logger.info(token)
        return token['access_token']


class DiasporaLogger:
    def __init__(self, bootstrap_servers, refresh_token):
        self._provider = GlobusAuthTokenProvider(refresh_token)
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            sasl_oauth_token_provider=self._provider,
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="OAUTHBEARER",
            api_version=(3, 5, 1),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def __getattr__(self, name):
        # Delegate attribute access to self._producer
        return getattr(self._producer, name)
