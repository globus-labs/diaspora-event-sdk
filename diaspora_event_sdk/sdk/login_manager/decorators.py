import functools
import logging

import globus_sdk

from .._environments import TOKEN_EXCHANGE

log = logging.getLogger(__name__)


def requires_login(func):
    """Decorator that initiates a new auth flow when
    an API auth error is raised.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (globus_sdk.AuthAPIError, globus_sdk.exc.api.GlobusAPIError) as e:
            if isinstance(e, globus_sdk.AuthAPIError) or e.http_status == 401:
                log.debug(
                    "Unauthorized API call (callable: %s).  Exception text: %s",
                    func.__name__,
                    e,
                )
                self.login_manager.run_login_flow()
                # Initiate a new web client with updated authorizer
                self.web_client = self.login_manager.get_web_client(
                    base_url=TOKEN_EXCHANGE
                )
                return func(self, *args, **kwargs)

    return wrapper
