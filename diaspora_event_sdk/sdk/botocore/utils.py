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
import io
import logging
import re

from .compat import (
    IPV6_ADDRZ_RE,
    UNSAFE_URL_CHARS,
    quote,
    urlparse,
)

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
