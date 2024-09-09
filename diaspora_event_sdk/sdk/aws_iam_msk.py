#  Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64

# import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

# import boto3
# import botocore.session
# import pkg_resources
from .botocore.auth import SigV4QueryAuth
from .botocore.awsrequest import AWSRequest

# from botocore.config import Config
from .botocore.credentials import Credentials

ENDPOINT_URL_TEMPLATE = "https://kafka.{}.amazonaws.com/"
DEFAULT_TOKEN_EXPIRY_SECONDS = 900
DEFAULT_STS_SESSION_NAME = "MSKSASLDefaultSession"
ACTION_TYPE = "Action"
ACTION_NAME = "kafka-cluster:Connect"
SIGNING_NAME = "kafka-cluster"
USER_AGENT_KEY = "User-Agent"
LIB_NAME = "aws-msk-iam-sasl-signer-python"


def __get_user_agent__():
    return f"{LIB_NAME}/1.0.1"


def __get_expiration_time_ms(request):
    """
    Private function that parses the url and gets the expiration time

    Args: request (AWSRequest): The signed aws request object
    """
    # Parse the signed request
    parsed_url = urlparse(request.url)
    parsed_ul_params = parse_qs(parsed_url.query)
    parsed_signing_time = datetime.strptime(
        parsed_ul_params["X-Amz-Date"][0], "%Y%m%dT%H%M%SZ"
    )

    # Make the datetime object timezone-aware
    signing_time = parsed_signing_time.replace(tzinfo=timezone.utc)

    # Convert the Unix timestamp to milliseconds
    expiration_timestamp_seconds = (
        int(signing_time.timestamp()) + DEFAULT_TOKEN_EXPIRY_SECONDS
    )

    # Get lifetime of token
    expiration_timestamp_ms = expiration_timestamp_seconds * 1000

    return expiration_timestamp_ms


def __construct_auth_token(region, aws_credentials):
    """
    Private function that constructs the authorization token using IAM
    Credentials.

    Args: region (str): The AWS region where the cluster is located.
    aws_credentials (dict): The credentials to be used to generate signed
    url. Returns: str: A base64-encoded authorization token.
    """
    # Validate credentials are not empty
    if not aws_credentials.access_key or not aws_credentials.secret_key:
        raise ValueError("AWS Credentials can not be empty")

    # Extract endpoint URL
    endpoint_url = ENDPOINT_URL_TEMPLATE.format(region)

    # Set up resource path and query parameters
    query_params = {ACTION_TYPE: ACTION_NAME}

    # Create SigV4 instance
    sig_v4 = SigV4QueryAuth(
        aws_credentials, SIGNING_NAME, region, expires=DEFAULT_TOKEN_EXPIRY_SECONDS
    )

    # Create request with url and parameters
    request = AWSRequest(method="GET", url=endpoint_url, params=query_params)

    # Add auth to the request and prepare the request
    sig_v4.add_auth(request)
    query_params = {USER_AGENT_KEY: __get_user_agent__()}
    request.params = query_params
    prepped = request.prepare()

    # Get the signed url
    signed_url = prepped.url

    # Base 64 encode and remove the padding from the end
    signed_url_bytes = signed_url.encode("utf-8")
    base64_bytes = base64.urlsafe_b64encode(signed_url_bytes)
    base64_encoded_signed_url = base64_bytes.decode("utf-8").rstrip("=")
    return base64_encoded_signed_url, __get_expiration_time_ms(request)


def generate_auth_token(region, aws_debug_creds=False):
    """
    Generates an base64-encoded signed url as auth token to authenticate
    with an Amazon MSK cluster using default IAM credentials.

    Args:
        region (str): The AWS region where the cluster is located.
    Returns:
        str: A base64-encoded authorization token.
    """

    # Load credentials
    import os

    assert os.environ["OCTOPUS_AWS_ACCESS_KEY_ID"]
    assert os.environ["OCTOPUS_AWS_SECRET_ACCESS_KEY"]

    aws_credentials = Credentials(
        os.environ["OCTOPUS_AWS_ACCESS_KEY_ID"],
        os.environ["OCTOPUS_AWS_SECRET_ACCESS_KEY"],
    )

    return __construct_auth_token(region, aws_credentials)
