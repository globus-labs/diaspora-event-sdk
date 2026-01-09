from __future__ import annotations

import logging
import os
import sys
import threading
import typing as t

import globus_sdk
from globus_sdk.scopes import AuthScopes, ScopeBuilder
from diaspora_event_sdk.sdk.login_manager.tokenstore import get_token_storage_adapter

from .._environments import DIASPORA_RESOURCE_SERVER
from ..web_client import WebClient
from .client_login import get_client_login, is_client_login
from .globus_auth import internal_auth_client
from .login_flow import do_link_auth_flow

log = logging.getLogger(__name__)


class FilteredClientCredentialsAuthorizer(globus_sdk.ClientCredentialsAuthorizer):
    """
    A custom ClientCredentialsAuthorizer that filters token responses to only
    include tokens for a specific resource server.

    This is needed when client credentials return tokens for multiple resource
    servers, but ClientCredentialsAuthorizer expects exactly one token.
    """

    def __init__(
        self,
        confidential_client: globus_sdk.ConfidentialAppAuthClient,
        scopes: list[str],
        *,
        resource_server: str,
        access_token: str | None = None,
        expires_at: int | None = None,
        on_refresh: t.Callable[[globus_sdk.OAuthTokenResponse], None] | None = None,
    ) -> None:
        self._target_resource_server = resource_server
        # Store the original on_refresh callback
        self._original_on_refresh = on_refresh
        super().__init__(
            confidential_client=confidential_client,
            scopes=scopes,
            access_token=access_token,
            expires_at=expires_at,
            on_refresh=self._filtered_on_refresh,
        )

    def _extract_token_data(
        self, res: globus_sdk.OAuthClientCredentialsResponse
    ) -> dict[str, t.Any]:
        """
        Extract token data, filtering to only the target resource server.
        """
        token_data = res.by_resource_server
        if self._target_resource_server in token_data:
            # Return only the token for the target resource server
            return token_data[self._target_resource_server]
        else:
            raise ValueError(
                f"Token response does not contain token for {self._target_resource_server}"
            )

    def _filtered_on_refresh(
        self, token_response: globus_sdk.OAuthTokenResponse
    ) -> None:
        """
        Call the original on_refresh callback with the filtered token response.
        """
        if self._original_on_refresh:
            self._original_on_refresh(token_response)


def _get_diaspora_all_scope() -> str:
    return os.getenv(
        "DIASPORA_SCOPE",
        f"https://auth.globus.org/scopes/{DIASPORA_RESOURCE_SERVER}/action_all",
    )


class DiasporaScopeBuilder(ScopeBuilder):
    def __init__(self):
        super().__init__(DIASPORA_RESOURCE_SERVER)
        self.all = _get_diaspora_all_scope()


#: a ScopeBuilder in the style of globus_sdk.scopes for the Diaspora service
#: it supports one scope named 'action_all', as in ``DiasporaScopes.all``
DiasporaScopes = DiasporaScopeBuilder()


class LoginManager:
    """
    This class is primarily a wrapper over a sqlite tokenstorage adapter provided by the
    globus-sdk.
    See also: https://globus-sdk-python.readthedocs.io/en/stable/tokenstorage.html

    The purpose of the LoginManager is to hold a tokenstorage object and combine it with
    - a login flow which authenticates the user for the correct set of scopes
    - a helper method for ensuring that the user is logged in (only doing login if
      tokens are missing)
    - methods for building SDK client objects with correct RefreshTokenAuthorizer
      authorizers
    """

    SCOPES: dict[str, list[str]] = {
        DiasporaScopes.resource_server: [DiasporaScopes.all],
        AuthScopes.resource_server: [AuthScopes.openid],
    }

    def __init__(self, *, environment: str | None = None) -> None:
        self._token_storage = get_token_storage_adapter(environment=environment)
        self._access_lock = threading.Lock()

    @property
    def login_requirements(self) -> t.Iterator[tuple[str, list[str]]]:
        yield from self.SCOPES.items()

    @staticmethod
    def is_jupyter():
        # Simplest way to find out if we are in Jupyter without having to
        # check imports
        return "jupyter_core" in sys.modules

    def run_login_flow(
        self,
        *,
        scopes: list[str] | None = None,
    ):
        if is_client_login():
            # We don't need a login flow for a client login
            return

        # The authorization-via-weblink flow requires stdin; the user must visit
        # the weblink and enter generated code.
        if (
            not sys.stdin.isatty() or sys.stdin.closed
        ) and not LoginManager.is_jupyter():
            # Not technically necessary; the login flow would just die with an EOF
            # during input(), but adding this message here is much more direct --
            # handle the non-happy path by letting the user know precisely the issue
            raise RuntimeError(
                "Unable to run native app login flow: stdin is closed or is not a TTY."
            )

        if scopes is None:  # flatten scopes to list of strings if none provided
            scopes = [
                s for _rs_name, rs_scopes in self.login_requirements for s in rs_scopes
            ]

        token = do_link_auth_flow(scopes)
        with self._access_lock:
            self._token_storage.store(token)

    def logout(self) -> bool:
        """
        Returns True if at least one set of tokens were found and revoked.
        """
        with self._access_lock:
            auth_client = internal_auth_client()
            tokens_revoked = False
            for rs, token_data in self._token_storage.get_by_resource_server().items():
                for tok_key in ("access_token", "refresh_token"):
                    token = token_data[tok_key]
                    auth_client.oauth2_revoke_token(token)
                self._token_storage.remove_tokens_for_resource_server(rs)
                tokens_revoked = True

        return tokens_revoked

    def ensure_logged_in(self) -> None:
        """Ensures that the user has valid refresh tokens. If a token
        is found to be invalid, a new login flow is initiated.
        """
        with self._access_lock:
            data = self._token_storage.get_by_resource_server()

        for server, _scopes in self.login_requirements:
            if server not in data:
                self.run_login_flow()
                break

    def _get_authorizer(
        self, resource_server: str
    ) -> globus_sdk.authorizers.RenewingAuthorizer:
        log.debug("build authorizer for %s", resource_server)
        tokens = self._token_storage.get_token_data(resource_server)

        if is_client_login():
            # construct scopes for the specified resource server.
            # this is not guaranteed to contain always required scopes,
            # additional logic may be needed to handle client identities that
            # may be missing those.
            scopes = []
            for rs_name, rs_scopes in self.login_requirements:
                if rs_name == resource_server:
                    scopes.extend(rs_scopes)

            # if we already have a token use it. This token could be invalid
            # or for another client, but automatic retries will handle that
            access_token = None
            expires_at = None
            if tokens:
                access_token = tokens["access_token"]
                expires_at = tokens["expires_at_seconds"]

            with self._access_lock:
                # Use a custom authorizer that filters token responses to only
                # the requested resource server, handling cases where client
                # credentials return tokens for multiple resource servers
                return FilteredClientCredentialsAuthorizer(
                    confidential_client=get_client_login(),
                    scopes=scopes,
                    resource_server=resource_server,
                    access_token=access_token,
                    expires_at=expires_at,
                    on_refresh=self._token_storage.on_refresh,
                )
        else:
            if tokens is None:
                raise LookupError(
                    f"LoginManager could not find tokens for {resource_server}"
                )
            with self._access_lock:
                return globus_sdk.RefreshTokenAuthorizer(
                    tokens["refresh_token"],
                    internal_auth_client(),
                    access_token=tokens["access_token"],
                    expires_at=tokens["expires_at_seconds"],
                    on_refresh=self._token_storage.on_refresh,
                )

    def get_auth_client(self) -> globus_sdk.AuthClient:
        return globus_sdk.AuthClient(
            authorizer=self._get_authorizer(AuthScopes.resource_server)
        )

    def get_web_client(
        self, *, base_url: str | None = None, app_name: str | None = None
    ) -> WebClient:
        return WebClient(
            base_url=base_url,
            app_name=app_name,
            authorizer=self._get_authorizer(DiasporaScopes.resource_server),
        )
