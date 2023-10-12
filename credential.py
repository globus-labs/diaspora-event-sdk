import webbrowser
import base64
import hashlib
import os
import http.client
import urllib.parse
import json


def generate_code_verifier_and_challenge():
    code_verifier = base64.urlsafe_b64encode(
        os.urandom(32)).decode("utf-8").rstrip("=")
    hashed_verifier = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(
        hashed_verifier).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def build_authorization_url(code_challenge):
    params = {
        "client_id": "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe",
        "redirect_uri": "https://auth.globus.org/v2/web/auth-code",
        "scope": "openid email profile offline_access https://auth.globus.org/scopes/2b9d2f5c-fa32-45b5-875b-b24cd343b917/action_all",
        "state": "_default",
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    param_str = urllib.parse.urlencode(params)
    return f"https://auth.globus.org/v2/oauth2/authorize?{param_str}"


def request_token(code, code_verifier):
    conn = http.client.HTTPSConnection("auth.globus.org")
    params = urllib.parse.urlencode({
        "client_id": "c5d4fab4-7f0d-422e-b0c8-5c74329b52fe",
        "redirect_uri": "https://auth.globus.org/v2/web/auth-code",
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier
    })
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    conn.request("POST", "/v2/oauth2/token", body=params, headers=headers)
    response = conn.getresponse()
    response_body = response.read().decode()
    conn.close()

    if response.status == 200:
        return json.loads(response_body)
    else:
        print(f"Failed to retrieve access token: {response_body}")


def decode_jwt(jwt):
    payload = jwt.split('.')[1]
    payload_padding = len(payload) % 4
    payload += "="*payload_padding
    payload_decoded = json.loads(
        base64.urlsafe_b64decode(payload).decode('utf-8'))

    return payload_decoded


def claim_topics(sub):
    conn = http.client.HTTPConnection("52.200.217.146:9090")
    conn.request("POST", f"/acl?sub={sub}")
    print(f"POSTing to the ACL endpoint with /acl?sub={sub}")

    response = conn.getresponse()
    response_body = response.read().decode()
    conn.close()

    if response.status == 200:
        print(f"Successful registration: {response_body}")
    else:
        print(f"Failed to register: {response_body}")


def request_token_workflow():
    code_verifier, code_challenge = generate_code_verifier_and_challenge()
    authorization_url = build_authorization_url(code_challenge)
    print(
        f"Please visit the following URL to authorize the application:\n{authorization_url}")
    webbrowser.open(authorization_url)
    authorization_code = input("Paste the authorization code here: ").strip()
    token = request_token(authorization_code, code_verifier)
    if token:
        refresh_token = token['other_tokens'][0]['refresh_token']
        print("\n***")
        print("For Python clients (e.g., example_producer.py and example_consumer.py):")
        print(f"export DIASPORA_REFRESH={refresh_token}")
        print("***")

        payload = decode_jwt(token['id_token'])
        preferred_username = payload['preferred_username'].split("@")[0]
        print("credential subject claim:", payload['sub'])
        print("credential subject username:", preferred_username)

        # print("For Java clients (kafka-oauth2-0.0.x.jar):")
        # print(f"save to {preferred_username}.properties")
        # print("security.protocol=SASL_PLAINTEXT")
        # print("sasl.mechanism=OAUTHBEARER")
        # print("sasl.login.callback.handler.class=com.oauth2.security.oauthbearer.OAuthAuthenticateLoginCallbackHandler")
        # print("sasl.jaas.config=org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required \\")
        # print(f"     OAUTH_REFRESH_TOKEN='{refresh_token}';")


if __name__ == "__main__":
    request_token_workflow()
