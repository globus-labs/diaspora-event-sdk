"""A consumer that reads topics over the web service's REST consumer routes."""

from __future__ import annotations

import logging
import typing as t
import urllib.parse
from collections.abc import Iterable, Mapping

import globus_sdk

from ._rest_records import decode_binary_record
from .client import Client
from .web_client import WebAPIError

if t.TYPE_CHECKING:
    from typing_extensions import Self

logger = logging.getLogger(__name__)

#: A topic and a partition. Every topic has one partition, 0.
TopicPartitionT = tuple[str, int]

V2_CONTENT_TYPE = "application/vnd.kafka.v2+json"
INSTANCE_NOT_FOUND = 40403


class RESTConsumer:
    """A consumer instance of the web service's REST consumer API.

    The routes are those of Confluent REST Proxy v2, under
    ``/api/v2/consumers``, and act in the client's default namespace:
    topics are named without the namespace, and the group ``my-group`` is
    the Kafka consumer group ``<namespace>.my-group``. Every topic has one
    partition, 0, and a partition is a ``(topic, partition)`` tuple, so a
    ``kafka.TopicPartition`` works too.

    Creating a ``RESTConsumer`` creates the instance on the service, and
    ``close()``, or the end of a ``with`` block, deletes it::

        with RESTConsumer("my-group", format="json",
                          auto_offset_reset="earliest") as consumer:
            consumer.subscribe(["my-topic"])
            for record in consumer.fetch(timeout_ms=5000):
                print(record["offset"], record["value"])
            consumer.commit()

    A ``binary`` instance returns each record's key, value and header
    values as bytes; a ``json`` instance returns them as the service gives
    them: JSON keys and values as JSON values, text as str, and header
    values in base64.

    The service drops every instance when it is deployed or restarted, and
    closes an instance idle for 5 minutes (the service's default). A
    request for an instance that is gone gets 404 with error code 40403.
    With ``recover=True``, the default, the consumer then creates the
    instance again with the same name and settings, subscribes to the same
    topics or assigns the same partitions, and retries the request once.
    It recovers from no other error.
    The new instance starts from the group's committed offsets, so records
    fetched since the last commit can come again, and positions set by a
    seek are lost. A consumer that needs each record once should carry an
    id in the record and drop repeats. A group that never committed starts
    where ``auto_offset_reset`` says. A subscribed instance gets its
    partitions at its first fetch, so a seek or a commit with offsets that
    is retried on a new subscribed instance is refused with 409 (40903)
    until the instance has fetched.

    Errors raise :class:`~diaspora_event_sdk.sdk.web_client.WebAPIError`,
    whose ``error_code`` is the service's code. The web client retries
    429, 500, 502, 503 and 504 replies, as globus-sdk does by default.
    """

    def __init__(
        self,
        group: str,
        *,
        client: Client | None = None,
        name: str | None = None,
        format: t.Literal["binary", "json"] = "binary",
        auto_offset_reset: t.Literal["earliest", "latest", "none"] | None = None,
        auto_commit_enable: bool | None = None,
        fetch_min_bytes: int | None = None,
        consumer_request_timeout_ms: int | None = None,
        recover: bool = True,
    ) -> None:
        """Create a consumer instance in a group.

        :param group: The consumer group, without the namespace.
        :param client: The client to authenticate with; a new ``Client()``
            if not given.
        :param name: The instance's name, unique in the group; the service
            picks one if not given.
        :param format: ``"binary"`` or ``"json"``, how records are returned.
        :param auto_offset_reset: Where a group that has not committed
            starts: ``"earliest"``, ``"latest"`` (the service's default) or
            ``"none"``.
        :param auto_commit_enable: Whether the instance commits its
            positions by itself; the service's default is False.
        :param fetch_min_bytes: The Kafka consumer's ``fetch.min.bytes``.
        :param consumer_request_timeout_ms: How long a fetch that names no
            timeout waits for records; the service's default is 5000.
        :param recover: Whether to create the instance again and retry once
            when the service answers that it is gone (40403).
        """
        self.group = group
        self.format = format
        self._client = client if client is not None else Client()
        self._web = self._client.web_client
        self._recover = recover
        settings: dict[str, t.Any] = {
            "format": format,
            "auto.offset.reset": auto_offset_reset,
            # the service takes the strings "true" and "false"
            "auto.commit.enable": None
            if auto_commit_enable is None
            else str(auto_commit_enable).lower(),
            "fetch.min.bytes": fetch_min_bytes,
            "consumer.request.timeout.ms": consumer_request_timeout_ms,
        }
        self._settings = {k: v for k, v in settings.items() if v is not None}
        self._topics: list[str] = []
        self._partitions: list[TopicPartitionT] = []
        self._closed = False
        self.name: str | None = name
        self.base_uri = ""
        self._create()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"RESTConsumer(group={self.group!r}, name={self.name!r})"

    @property
    def closed(self) -> bool:
        """Whether ``close()`` has deleted the instance."""
        return self._closed

    def subscribe(self, topics: Iterable[str]) -> None:
        """Subscribe to topics, named without the namespace.

        The group assigns the topics' partitions at the next fetch.
        """
        names = [topics] if isinstance(topics, str) else list(topics)
        self._request("POST", "/subscription", data={"topics": names})
        self._topics, self._partitions = names, []

    def subscription(self) -> list[str]:
        """Return the topics the instance is subscribed to."""
        return list(self._request("GET", "/subscription").data["topics"])

    def unsubscribe(self) -> None:
        """Unsubscribe from every topic."""
        self._request("DELETE", "/subscription")
        self._topics = []

    def assign(self, partitions: Iterable[TopicPartitionT]) -> None:
        """Assign partitions to the instance, in place of a subscription."""
        assigned = [(topic, partition) for topic, partition in partitions]
        self._request(
            "POST", "/assignments", data={"partitions": _partitions(assigned)}
        )
        self._topics, self._partitions = [], assigned

    def assignment(self) -> list[TopicPartitionT]:
        """Return the partitions assigned to the instance."""
        data = self._request("GET", "/assignments").data
        return [(p["topic"], p["partition"]) for p in data["partitions"]]

    def fetch(
        self, timeout_ms: int | None = None, max_bytes: int | None = None
    ) -> list[dict[str, t.Any]]:
        """Fetch the next records.

        Each record is a dict of ``topic``, ``key``, ``value``,
        ``partition``, ``offset`` and ``headers``, a list of ``{"name",
        "value"}``. A binary instance's keys, values and header values are
        bytes.

        :param timeout_ms: How long to wait for records, at most 30000; the
            instance's ``consumer_request_timeout_ms`` if not given.
        :param max_bytes: Bytes of keys and values the reply stays under,
            except that the first record is returned however large.
        :returns: The records, or an empty list if none came in time.
        """
        query: dict[str, t.Any] = {}
        if timeout_ms is not None:
            query["timeout"] = timeout_ms
        if max_bytes is not None:
            query["max_bytes"] = max_bytes
        accept = f"application/vnd.kafka.{self.format}.v2+json"
        records = self._request(
            "GET", "/records", query_params=query, accept=accept
        ).data
        if self.format == "binary":
            return [decode_binary_record(record) for record in records]
        return list(records)

    def commit(self, offsets: Mapping[TopicPartitionT, int] | None = None) -> None:
        """Commit offsets for the group.

        :param offsets: For each partition, the offset of the last record
            processed; the group commits the one after it. If not given,
            commits the position of each assigned partition, the record
            after the last one fetched.
        """
        data = None
        if offsets is not None:
            data = {"offsets": _offsets(offsets)}
        self._request("POST", "/offsets", data=data)

    def committed(
        self, partitions: Iterable[TopicPartitionT]
    ) -> dict[TopicPartitionT, int]:
        """Return the group's committed offsets, the next record to read.

        A partition the group has not committed is left out.
        """
        data = self._request(
            "GET", "/offsets", data={"partitions": _partitions(partitions)}
        ).data
        return {(o["topic"], o["partition"]): o["offset"] for o in data["offsets"]}

    def seek(self, offsets: Mapping[TopicPartitionT, int]) -> None:
        """Set the offset the next fetch reads from in each partition.

        The partitions must be assigned to the instance.
        """
        self._request("POST", "/positions", data={"offsets": _offsets(offsets)})

    def seek_to_beginning(self, partitions: Iterable[TopicPartitionT] = ()) -> None:
        """Seek partitions to their first record; every assigned one if none."""
        self._request(
            "POST", "/positions/beginning", data={"partitions": _partitions(partitions)}
        )

    def seek_to_end(self, partitions: Iterable[TopicPartitionT] = ()) -> None:
        """Seek partitions past their last record; every assigned one if none."""
        self._request(
            "POST", "/positions/end", data={"partitions": _partitions(partitions)}
        )

    def close(self) -> None:
        """Delete the instance. An instance the service already dropped is
        taken as deleted. Closing twice does nothing."""
        if self._closed:
            return
        try:
            self._send("DELETE", "")
        except WebAPIError as err:
            if not _instance_gone(err):
                raise
        self._closed = True

    def _create(self) -> None:
        settings = dict(self._settings)
        if self.name is not None:
            settings["name"] = self.name
        group = urllib.parse.quote(self.group, safe="")
        url = f"{self._web.base_url.rstrip('/')}/api/v2/consumers/{group}"
        reply = self._web.post(
            url, data=settings, headers=self._headers(), encoding="json"
        )
        self.name = reply.data["instance_id"]
        self.base_uri = reply.data["base_uri"]

    def _recreate(self) -> None:
        logger.info(
            "Consumer instance %s of group %s is gone; creating it again",
            self.name,
            self.group,
        )
        self._create()
        if self._topics:
            self._send("POST", "/subscription", data={"topics": self._topics})
        elif self._partitions:
            self._send(
                "POST",
                "/assignments",
                data={"partitions": _partitions(self._partitions)},
            )

    def _request(
        self,
        method: str,
        route: str,
        *,
        data: dict[str, t.Any] | None = None,
        query_params: dict[str, t.Any] | None = None,
        accept: str | None = None,
    ) -> globus_sdk.GlobusHTTPResponse:
        if self._closed:
            raise RuntimeError(f"{self!r} is closed")
        try:
            return self._send(
                method, route, data=data, query_params=query_params, accept=accept
            )
        except WebAPIError as err:
            if not (self._recover and _instance_gone(err)):
                raise
        self._recreate()
        return self._send(
            method, route, data=data, query_params=query_params, accept=accept
        )

    def _send(
        self,
        method: str,
        route: str,
        *,
        data: dict[str, t.Any] | None = None,
        query_params: dict[str, t.Any] | None = None,
        accept: str | None = None,
    ) -> globus_sdk.GlobusHTTPResponse:
        headers = self._headers()
        if accept is not None:
            headers["Accept"] = accept
        return self._web.request(
            method,
            self.base_uri + route,
            data=data,
            query_params=query_params,
            headers=headers,
            encoding="json" if data is not None else None,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Subject": str(self._client.subject_openid),
            "Content-Type": V2_CONTENT_TYPE,
        }


def _instance_gone(err: WebAPIError) -> bool:
    return err.http_status == 404 and err.error_code == INSTANCE_NOT_FOUND


def _partitions(partitions: Iterable[TopicPartitionT]) -> list[dict[str, t.Any]]:
    return [{"topic": topic, "partition": partition} for topic, partition in partitions]


def _offsets(offsets: Mapping[TopicPartitionT, int]) -> list[dict[str, t.Any]]:
    return [
        {"topic": topic, "partition": partition, "offset": offset}
        for (topic, partition), offset in offsets.items()
    ]
