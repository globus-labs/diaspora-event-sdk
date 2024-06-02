# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
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
# import functools
import logging
from collections.abc import Mapping

from .compat import (
    HTTPHeaders,
    MutableMapping,
    urlencode,
    urlparse,
)
from .exceptions import UnseekableStreamError
from .utils import determine_content_length

logger = logging.getLogger(__name__)


class AWSRequestPreparer:
    """
    This class performs preparation on AWSRequest objects similar to that of
    the PreparedRequest class does in the requests library. However, the logic
    has been boiled down to meet the specific use cases in botocore. Of note
    there are the following differences:
        This class does not heavily prepare the URL. Requests performed many
        validations and corrections to ensure the URL is properly formatted.
        Botocore either performs these validations elsewhere or otherwise
        consistently provides well formatted URLs.

        This class does not heavily prepare the body. Body preperation is
        simple and supports only the cases that we document: bytes and
        file-like objects to determine the content-length. This will also
        additionally prepare a body that is a dict to be url encoded params
        string as some signers rely on this. Finally, this class does not
        support multipart file uploads.

        This class does not prepare the method, auth or cookies.
    """

    def prepare(self, original):
        method = original.method
        url = self._prepare_url(original)
        body = self._prepare_body(original)
        headers = self._prepare_headers(original, body)
        stream_output = original.stream_output

        return AWSPreparedRequest(method, url, headers, body, stream_output)

    def _prepare_url(self, original):
        url = original.url
        if original.params:
            url_parts = urlparse(url)
            delim = '&' if url_parts.query else '?'
            if isinstance(original.params, Mapping):
                params_to_encode = list(original.params.items())
            else:
                params_to_encode = original.params
            params = urlencode(params_to_encode, doseq=True)
            url = delim.join((url, params))
        return url

    def _prepare_headers(self, original, prepared_body=None):
        headers = HeadersDict(original.headers.items())

        # If the transfer encoding or content length is already set, use that
        if 'Transfer-Encoding' in headers or 'Content-Length' in headers:
            return headers

        # Ensure we set the content length when it is expected
        if original.method not in ('GET', 'HEAD', 'OPTIONS'):
            length = self._determine_content_length(prepared_body)
            if length is not None:
                headers['Content-Length'] = str(length)
            else:
                # Failed to determine content length, using chunked
                # NOTE: This shouldn't ever happen in practice
                body_type = type(prepared_body)
                logger.debug('Failed to determine length of %s', body_type)
                headers['Transfer-Encoding'] = 'chunked'

        return headers

    def _to_utf8(self, item):
        key, value = item
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(value, str):
            value = value.encode('utf-8')
        return key, value

    def _prepare_body(self, original):
        """Prepares the given HTTP body data."""
        body = original.data
        if body == b'':
            body = None

        if isinstance(body, dict):
            params = [self._to_utf8(item) for item in body.items()]
            body = urlencode(params, doseq=True)

        return body

    def _determine_content_length(self, body):
        return determine_content_length(body)


class AWSRequest:
    """Represents the elements of an HTTP request.

    This class was originally inspired by requests.models.Request, but has been
    boiled down to meet the specific use cases in botocore. That being said this
    class (even in requests) is effectively a named-tuple.
    """

    _REQUEST_PREPARER_CLS = AWSRequestPreparer

    def __init__(
        self,
        method=None,
        url=None,
        headers=None,
        data=None,
        params=None,
        auth_path=None,
        stream_output=False,
    ):
        self._request_preparer = self._REQUEST_PREPARER_CLS()

        # Default empty dicts for dict params.
        params = {} if params is None else params

        self.method = method
        self.url = url
        self.headers = HTTPHeaders()
        self.data = data
        self.params = params
        self.auth_path = auth_path
        self.stream_output = stream_output

        if headers is not None:
            for key, value in headers.items():
                self.headers[key] = value

        # This is a dictionary to hold information that is used when
        # processing the request. What is inside of ``context`` is open-ended.
        # For example, it may have a timestamp key that is used for holding
        # what the timestamp is when signing the request. Note that none
        # of the information that is inside of ``context`` is directly
        # sent over the wire; the information is only used to assist in
        # creating what is sent over the wire.
        self.context = {}

    def prepare(self):
        """Constructs a :class:`AWSPreparedRequest <AWSPreparedRequest>`."""
        return self._request_preparer.prepare(self)

    @property
    def body(self):
        body = self.prepare().body
        if isinstance(body, str):
            body = body.encode('utf-8')
        return body


class AWSPreparedRequest:
    """A data class representing a finalized request to be sent over the wire.

    Requests at this stage should be treated as final, and the properties of
    the request should not be modified.

    :ivar method: The HTTP Method
    :ivar url: The full url
    :ivar headers: The HTTP headers to send.
    :ivar body: The HTTP body.
    :ivar stream_output: If the response for this request should be streamed.
    """

    def __init__(self, method, url, headers, body, stream_output):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.stream_output = stream_output

    def __repr__(self):
        fmt = (
            '<AWSPreparedRequest stream_output=%s, method=%s, url=%s, '
            'headers=%s>'
        )
        return fmt % (self.stream_output, self.method, self.url, self.headers)

    def reset_stream(self):
        """Resets the streaming body to it's initial position.

        If the request contains a streaming body (a streamable file-like object)
        seek to the object's initial position to ensure the entire contents of
        the object is sent. This is a no-op for static bytes-like body types.
        """
        # Trying to reset a stream when there is a no stream will
        # just immediately return.  It's not an error, it will produce
        # the same result as if we had actually reset the stream (we'll send
        # the entire body contents again if we need to).
        # Same case if the body is a string/bytes/bytearray type.

        non_seekable_types = (bytes, str, bytearray)
        if self.body is None or isinstance(self.body, non_seekable_types):
            return
        try:
            logger.debug("Rewinding stream: %s", self.body)
            self.body.seek(0)
        except Exception as e:
            logger.debug("Unable to rewind stream: %s", e)
            raise UnseekableStreamError(stream_object=self.body)


class _HeaderKey:
    def __init__(self, key):
        self._key = key
        self._lower = key.lower()

    def __hash__(self):
        return hash(self._lower)

    def __eq__(self, other):
        return isinstance(other, _HeaderKey) and self._lower == other._lower

    def __str__(self):
        return self._key

    def __repr__(self):
        return repr(self._key)


class HeadersDict(MutableMapping):
    """A case-insenseitive dictionary to represent HTTP headers."""

    def __init__(self, *args, **kwargs):
        self._dict = {}
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        self._dict[_HeaderKey(key)] = value

    def __getitem__(self, key):
        return self._dict[_HeaderKey(key)]

    def __delitem__(self, key):
        del self._dict[_HeaderKey(key)]

    def __iter__(self):
        return (str(key) for key in self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return repr(self._dict)

    def copy(self):
        return HeadersDict(self.items())
