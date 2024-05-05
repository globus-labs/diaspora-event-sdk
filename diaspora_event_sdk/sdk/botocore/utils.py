# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
# import base64
# import binascii
# import datetime
# import email.message
# import functools
# import hashlib
import io
import logging
# import os
# import random
import re
# import socket
# import time
# import warnings
# import weakref
# from datetime import datetime as _DatetimeClass
# from ipaddress import ip_address
# from pathlib import Path
# from urllib.request import getproxies, proxy_bypass

# import dateutil.parser
# from dateutil.tz import tzutc
# from urllib3.exceptions import LocationParseError

# import botocore
# import botocore.awsrequest
# import botocore.httpsession

# IP Regexes retained for backwards compatibility
# from botocore.compat import HEX_PAT  # noqa: F401
# from botocore.compat import IPV4_PAT  # noqa: F401
# from botocore.compat import IPV6_ADDRZ_PAT  # noqa: F401
# from botocore.compat import IPV6_PAT  # noqa: F401
# from botocore.compat import LS32_PAT  # noqa: F401
# from botocore.compat import UNRESERVED_PAT  # noqa: F401
# from botocore.compat import ZONE_ID_PAT  # noqa: F401
from .compat import (
    # HAS_CRT,
    # IPV4_RE,
    IPV6_ADDRZ_RE,
    # MD5_AVAILABLE,
    UNSAFE_URL_CHARS,
    # OrderedDict,
    # get_md5,
    # get_tzinfo_options,
    # json,
    quote,
    urlparse,
    # urlsplit,
    # urlunsplit,
    # zip_longest,
)
# from botocore.exceptions import (
#     ClientError,
#     ConfigNotFound,
#     ConnectionClosedError,
#     ConnectTimeoutError,
#     EndpointConnectionError,
#     HTTPClientError,
#     InvalidDNSNameError,
#     InvalidEndpointConfigurationError,
#     InvalidExpressionError,
#     InvalidHostLabelError,
#     InvalidIMDSEndpointError,
#     InvalidIMDSEndpointModeError,
#     InvalidRegionError,
#     MetadataRetrievalError,
#     MissingDependencyException,
#     ReadTimeoutError,
#     SSOTokenLoadError,
#     UnsupportedOutpostResourceError,
#     UnsupportedS3AccesspointConfigurationError,
#     UnsupportedS3ArnError,
#     UnsupportedS3ConfigurationError,
#     UnsupportedS3ControlArnError,
#     UnsupportedS3ControlConfigurationError,
# )

logger = logging.getLogger(__name__)
DEFAULT_METADATA_SERVICE_TIMEOUT = 1
METADATA_BASE_URL = 'http://169.254.169.254/'
METADATA_BASE_URL_IPv6 = 'http://[fd00:ec2::254]/'
METADATA_ENDPOINT_MODES = ('ipv4', 'ipv6')

# These are chars that do not need to be urlencoded.
# Based on rfc2986, section 2.3
SAFE_CHARS = '-._~'
LABEL_RE = re.compile(r'[a-z0-9][a-z0-9\-]*[a-z0-9]')
# RETRYABLE_HTTP_ERRORS = (
#     ReadTimeoutError,
#     EndpointConnectionError,
#     ConnectionClosedError,
#     ConnectTimeoutError,
# )
S3_ACCELERATE_WHITELIST = ['dualstack']
# In switching events from using service name / endpoint prefix to service
# id, we have to preserve compatibility. This maps the instances where either
# is different than the transformed service id.
EVENT_ALIASES = {
    "a4b": "alexa-for-business",
    "alexaforbusiness": "alexa-for-business",
    "api.mediatailor": "mediatailor",
    "api.pricing": "pricing",
    "api.sagemaker": "sagemaker",
    "apigateway": "api-gateway",
    "application-autoscaling": "application-auto-scaling",
    "appstream2": "appstream",
    "autoscaling": "auto-scaling",
    "autoscaling-plans": "auto-scaling-plans",
    "ce": "cost-explorer",
    "cloudhsmv2": "cloudhsm-v2",
    "cloudsearchdomain": "cloudsearch-domain",
    "cognito-idp": "cognito-identity-provider",
    "config": "config-service",
    "cur": "cost-and-usage-report-service",
    "data.iot": "iot-data-plane",
    "data.jobs.iot": "iot-jobs-data-plane",
    "data.mediastore": "mediastore-data",
    "datapipeline": "data-pipeline",
    "devicefarm": "device-farm",
    "devices.iot1click": "iot-1click-devices-service",
    "directconnect": "direct-connect",
    "discovery": "application-discovery-service",
    "dms": "database-migration-service",
    "ds": "directory-service",
    "dynamodbstreams": "dynamodb-streams",
    "elasticbeanstalk": "elastic-beanstalk",
    "elasticfilesystem": "efs",
    "elasticloadbalancing": "elastic-load-balancing",
    "elasticmapreduce": "emr",
    "elastictranscoder": "elastic-transcoder",
    "elb": "elastic-load-balancing",
    "elbv2": "elastic-load-balancing-v2",
    "email": "ses",
    "entitlement.marketplace": "marketplace-entitlement-service",
    "es": "elasticsearch-service",
    "events": "eventbridge",
    "cloudwatch-events": "eventbridge",
    "iot-data": "iot-data-plane",
    "iot-jobs-data": "iot-jobs-data-plane",
    "iot1click-devices": "iot-1click-devices-service",
    "iot1click-projects": "iot-1click-projects",
    "kinesisanalytics": "kinesis-analytics",
    "kinesisvideo": "kinesis-video",
    "lex-models": "lex-model-building-service",
    "lex-runtime": "lex-runtime-service",
    "logs": "cloudwatch-logs",
    "machinelearning": "machine-learning",
    "marketplace-entitlement": "marketplace-entitlement-service",
    "marketplacecommerceanalytics": "marketplace-commerce-analytics",
    "metering.marketplace": "marketplace-metering",
    "meteringmarketplace": "marketplace-metering",
    "mgh": "migration-hub",
    "models.lex": "lex-model-building-service",
    "monitoring": "cloudwatch",
    "mturk-requester": "mturk",
    "opsworks-cm": "opsworkscm",
    "projects.iot1click": "iot-1click-projects",
    "resourcegroupstaggingapi": "resource-groups-tagging-api",
    "route53": "route-53",
    "route53domains": "route-53-domains",
    "runtime.lex": "lex-runtime-service",
    "runtime.sagemaker": "sagemaker-runtime",
    "sdb": "simpledb",
    "secretsmanager": "secrets-manager",
    "serverlessrepo": "serverlessapplicationrepository",
    "servicecatalog": "service-catalog",
    "states": "sfn",
    "stepfunctions": "sfn",
    "storagegateway": "storage-gateway",
    "streams.dynamodb": "dynamodb-streams",
    "tagging": "resource-groups-tagging-api",
}


# This pattern can be used to detect if a header is a flexible checksum header
CHECKSUM_HEADER_PATTERN = re.compile(
    r'^X-Amz-Checksum-([a-z0-9]*)$',
    flags=re.IGNORECASE,
)


def determine_content_length(body):
    # No body, content length of 0
    if not body:
        return 0

    # Try asking the body for it's length
    try:
        return len(body)
    except (AttributeError, TypeError):
        pass

    # Try getting the length from a seekable stream
    if hasattr(body, 'seek') and hasattr(body, 'tell'):
        try:
            orig_pos = body.tell()
            body.seek(0, 2)
            end_file_pos = body.tell()
            body.seek(orig_pos)
            return end_file_pos - orig_pos
        except io.UnsupportedOperation:
            # in case when body is, for example, io.BufferedIOBase object
            # it has "seek" method which throws "UnsupportedOperation"
            # exception in such case we want to fall back to "chunked"
            # encoding
            pass
    # Failed to determine the length
    return None


def is_valid_ipv6_endpoint_url(endpoint_url):
    if UNSAFE_URL_CHARS.intersection(endpoint_url):
        return False
    hostname = f'[{urlparse(endpoint_url).hostname}]'
    return IPV6_ADDRZ_RE.match(hostname) is not None


def normalize_url_path(path):
    if not path:
        return '/'
    return remove_dot_segments(path)


def remove_dot_segments(url):
    # RFC 3986, section 5.2.4 "Remove Dot Segments"
    # Also, AWS services require consecutive slashes to be removed,
    # so that's done here as well
    if not url:
        return ''
    input_url = url.split('/')
    output_list = []
    for x in input_url:
        if x and x != '.':
            if x == '..':
                if output_list:
                    output_list.pop()
            else:
                output_list.append(x)

    if url[0] == '/':
        first = '/'
    else:
        first = ''
    if url[-1] == '/' and output_list:
        last = '/'
    else:
        last = ''
    return first + '/'.join(output_list) + last


def percent_encode_sequence(mapping, safe=SAFE_CHARS):
    """Urlencode a dict or list into a string.

    This is similar to urllib.urlencode except that:

    * It uses quote, and not quote_plus
    * It has a default list of safe chars that don't need
      to be encoded, which matches what AWS services expect.

    If any value in the input ``mapping`` is a list type,
    then each list element wil be serialized.  This is the equivalent
    to ``urlencode``'s ``doseq=True`` argument.

    This function should be preferred over the stdlib
    ``urlencode()`` function.

    :param mapping: Either a dict to urlencode or a list of
        ``(key, value)`` pairs.

    """
    encoded_pairs = []
    if hasattr(mapping, 'items'):
        pairs = mapping.items()
    else:
        pairs = mapping
    for key, value in pairs:
        if isinstance(value, list):
            for element in value:
                encoded_pairs.append(
                    f'{percent_encode(key)}={percent_encode(element)}'
                )
        else:
            encoded_pairs.append(
                f'{percent_encode(key)}={percent_encode(value)}'
            )
    return '&'.join(encoded_pairs)

def percent_encode(input_str, safe=SAFE_CHARS):
    """Urlencodes a string.

    Whereas percent_encode_sequence handles taking a dict/sequence and
    producing a percent encoded string, this function deals only with
    taking a string (not a dict/sequence) and percent encoding it.

    If given the binary type, will simply URL encode it. If given the
    text type, will produce the binary type by UTF-8 encoding the
    text. If given something else, will convert it to the text type
    first.
    """
    # If its not a binary or text string, make it a text string.
    if not isinstance(input_str, (bytes, str)):
        input_str = str(input_str)
    # If it's not bytes, make it bytes by UTF-8 encoding it.
    if not isinstance(input_str, bytes):
        input_str = input_str.encode('utf-8')
    return quote(input_str, safe=safe)
