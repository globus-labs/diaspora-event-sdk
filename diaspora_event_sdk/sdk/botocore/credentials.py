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

import logging
from collections import namedtuple

from .compat import ensure_unicode

logger = logging.getLogger(__name__)
ReadOnlyCredentials = namedtuple(
    'ReadOnlyCredentials', ['access_key', 'secret_key', 'token']
)

_DEFAULT_MANDATORY_REFRESH_TIMEOUT = 10 * 60  # 10 min
_DEFAULT_ADVISORY_REFRESH_TIMEOUT = 15 * 60  # 15 min


class Credentials:
    """
    Holds the credentials needed to authenticate requests.

    :param str access_key: The access key part of the credentials.
    :param str secret_key: The secret key part of the credentials.
    :param str token: The security token, valid only for session credentials.
    :param str method: A string which identifies where the credentials
        were found.
    """

    def __init__(self, access_key, secret_key, token=None, method=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token

        if method is None:
            method = 'explicit'
        self.method = method

        self._normalize()

    def _normalize(self):
        # Keys would sometimes (accidentally) contain non-ascii characters.
        # It would cause a confusing UnicodeDecodeError in Python 2.
        # We explicitly convert them into unicode to avoid such error.
        #
        # Eventually the service will decide whether to accept the credential.
        # This also complies with the behavior in Python 3.
        # self.access_key = botocore.compat.ensure_unicode(self.access_key)
        # self.secret_key = botocore.compat.ensure_unicode(self.secret_key)
        self.access_key = ensure_unicode(self.access_key)
        self.secret_key = ensure_unicode(self.secret_key)

    def get_frozen_credentials(self):
        return ReadOnlyCredentials(
            self.access_key, self.secret_key, self.token
        )
