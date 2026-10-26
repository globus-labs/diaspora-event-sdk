from __future__ import annotations

import contextvars
import os
import typing as t
import urllib.parse

import globus_sdk
import requests
import urllib3
from globus_sdk import Scope
from globus_sdk.transport import (
    RetryCheckResult,
    RetryConfig,
    RetryContext,
)
from globus_sdk.transport.default_retry_checks import check_retry_after_header

from diaspora_event_sdk.sdk.utils.uuid_like import UUID_LIKE_T

from ._environments import get_web_service_url

DIASPORA_RESOURCE_SERVER = "2b9d2f5c-fa32-45b5-875b-b24cd343b917"
DIASPORA_SCOPE = os.getenv(
    "DIASPORA_SCOPE",
    f"https://auth.globus.org/scopes/{DIASPORA_RESOURCE_SERVER}/action_all",
)


# Statuses the produce routes answer before they send any record, so a
# retry cannot write a record twice: 429 (42901) when the request is not
# admitted, and 503 (50302) when the service cannot reach the cluster. A
# 500 can come after the record was sent.
PRODUCE_RETRY_STATUSES = (429, 503)

# Set while a produce request is in flight in this thread or task
_producing: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "diaspora_producing", default=False
)


def _never_connected(error: BaseException | None) -> bool:
    """Whether a network error came before any connection was made."""
    if isinstance(error, requests.exceptions.ConnectTimeout):
        return True
    if isinstance(error, requests.exceptions.ConnectionError) and error.args:
        reason = getattr(error.args[0], "reason", None)
        return isinstance(reason, urllib3.exceptions.NewConnectionError)
    return False


def check_produce_retry(ctx: RetryContext) -> RetryCheckResult:
    """Limit the retries of a produce request to those that cannot write a
    record twice; leave other requests to globus-sdk's checks."""
    if not _producing.get():
        return RetryCheckResult.no_decision
    if ctx.response is None:
        if _never_connected(ctx.exception):
            return RetryCheckResult.do_retry
        return RetryCheckResult.do_not_retry
    status = ctx.response.status_code
    if status in PRODUCE_RETRY_STATUSES:
        # sets the wait from Retry-After when the reply has one
        return check_retry_after_header(ctx)
    if status == 401:
        # an expired token, refreshed by globus-sdk's check
        return RetryCheckResult.no_decision
    return RetryCheckResult.do_not_retry


class WebAPIError(globus_sdk.GlobusAPIError):
    """An error reply from the web service.

    The produce and consumer routes answer errors as Confluent's REST API
    does, with a JSON body of an ``error_code`` and a ``message``.
    """

    @property
    def error_code(self) -> int | None:
        """The reply's ``error_code``, such as 40403, or None if it has none."""
        data = self.raw_json
        code = data.get("error_code") if isinstance(data, dict) else None
        return code if isinstance(code, int) else None


class WebClient(globus_sdk.BaseClient):
    resource_server = DIASPORA_RESOURCE_SERVER
    error_class = WebAPIError

    @property
    def default_scope_requirements(self) -> list[Scope]:
        return [Scope(DIASPORA_SCOPE)]

    def __init__(
        self,
        *,
        environment: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        if base_url is None:
            base_url = get_web_service_url(environment)

        super().__init__(environment=environment, base_url=base_url, **kwargs)

    def _register_standard_retry_checks(self, retry_config: RetryConfig) -> None:
        retry_config.checks.register_check(check_produce_retry)
        super()._register_standard_retry_checks(retry_config)

    def create_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_user endpoint (POST /api/v3/user)."""
        return self.post("/api/v3/user", headers={"Subject": str(subject)})

    def delete_user(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_user endpoint (DELETE /api/v3/user)."""
        return self.delete("/api/v3/user", headers={"Subject": str(subject)})

    def create_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_key endpoint (POST /api/v3/key)."""
        return self.post("/api/v3/key", headers={"Subject": str(subject)})

    def delete_key(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_key endpoint (DELETE /api/v3/key)."""
        return self.delete("/api/v3/key", headers={"Subject": str(subject)})

    def list_namespaces(self, subject: UUID_LIKE_T) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 list_namespaces endpoint (GET /api/v3/namespace)."""
        return self.get("/api/v3/namespace", headers={"Subject": str(subject)})

    def create_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 create_topic endpoint (POST /api/v3/{namespace}/{topic})."""
        return self.post(
            f"/api/v3/{namespace}/{topic}", headers={"Subject": str(subject)}
        )

    def delete_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 delete_topic endpoint (DELETE /api/v3/{namespace}/{topic})."""
        return self.delete(
            f"/api/v3/{namespace}/{topic}", headers={"Subject": str(subject)}
        )

    def recreate_topic(
        self, subject: UUID_LIKE_T, namespace: str, topic: str
    ) -> globus_sdk.GlobusHTTPResponse:
        """Call the v3 recreate_topic endpoint (PUT /api/v3/{namespace}/{topic}/recreate)."""
        return self.put(
            f"/api/v3/{namespace}/{topic}/recreate",
            headers={"Subject": str(subject)},
        )

    def produce_record(
        self,
        subject: UUID_LIKE_T,
        namespace: str,
        topic: str,
        record: dict[str, t.Any],
    ) -> globus_sdk.GlobusHTTPResponse:
        """Produce one record (POST /api/v3/{namespace}/topics/{topic}/records).

        The record is in the body form of Confluent's REST API v3. The
        request is retried only on 429 and 503, which the service answers
        before it sends the record, and on a network error that came before
        a connection was made.
        """
        return self._produce(
            self._topic_url(namespace, topic, "records"), record, subject
        )

    def produce_records_batch(
        self,
        subject: UUID_LIKE_T,
        namespace: str,
        topic: str,
        entries: list[dict[str, t.Any]],
    ) -> globus_sdk.GlobusHTTPResponse:
        """Produce a batch of records (POST .../topics/{topic}/records:batch).

        Each entry is a record in the body form of Confluent's REST API v3,
        with an ``id``. The service answers 207 with each entry's outcome.
        Retries are as for ``produce_record``.
        """
        return self._produce(
            self._topic_url(namespace, topic, "records:batch"),
            {"entries": entries},
            subject,
        )

    def _produce(
        self, url: str, body: dict[str, t.Any], subject: UUID_LIKE_T
    ) -> globus_sdk.GlobusHTTPResponse:
        token = _producing.set(True)
        try:
            return self.post(url, data=body, headers={"Subject": str(subject)})
        finally:
            _producing.reset(token)

    def _topic_url(self, namespace: str, topic: str, route: str) -> str:
        # globus-sdk percent-encodes a relative path, colons included, so
        # "records:batch" would be sent as "records%3Abatch". An absolute
        # URL is sent as given, so the names are quoted here instead.
        ns, tp = (urllib.parse.quote(part, safe="") for part in (namespace, topic))
        return f"{self.base_url.rstrip('/')}/api/v3/{ns}/topics/{tp}/{route}"
