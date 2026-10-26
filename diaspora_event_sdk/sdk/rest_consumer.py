"""A consumer that reads topics over the web service's REST consumer routes."""

from __future__ import annotations

import logging
import threading
import typing as t
import urllib.parse
from collections.abc import Iterable, Mapping

import globus_sdk

from ._rest_records import decode_record
from .client import Client
from .web_client import WebAPIError

if t.TYPE_CHECKING:
    from typing_extensions import Self

logger = logging.getLogger(__name__)

#: A topic and a partition. Every topic has one partition, 0.
TopicPartitionT = tuple[str, int]

V2_CONTENT_TYPE = "application/vnd.kafka.v2+json"
INSTANCE_NOT_FOUND = 40403


class CommitLostError(WebAPIError):
    """A commit without offsets found its consumer instance gone.

    The service answered 404 with error code 40403, so nothing was
    committed. The consumer has created its instance again, and the next
    fetch resumes at the group's last commit, so the records fetched
    since that commit come again.
    """

    def _post_parse_hook(self) -> bool:
        self.messages = [
            (
                "The consumer instance was gone (40403), so nothing was "
                "committed. The instance has been created again; the next "
                "fetch resumes at the group's last commit."
            )
        ]
        return True


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

    A ``binary`` instance returns each record's key and value as bytes. A
    ``json`` instance returns a key or value that is one JSON value as that
    value, and other text as str: a key produced as the text ``42`` comes
    back as the number 42. Read with a ``binary`` instance to get the bytes
    as written. Header values are bytes in both formats.

    The service drops every instance when it is deployed or restarted, and
    closes an instance idle for 5 minutes (the service's default). The
    idle time runs while the caller processes the records of a fetch. A
    request for an instance that is gone gets 404 with error code 40403.
    With ``recover=True``, the default, the consumer then creates the
    instance again with the same name and settings, subscribes to the same
    topics or assigns the same partitions, and retries the request once.
    It recovers from no other error.

    The new instance starts from the group's committed offsets, so records
    fetched since the last commit can come again, and positions set by a
    seek are lost. A consumer that needs each record once should carry an
    id in the record and drop repeats. A group that never committed starts
    where ``auto_offset_reset`` says.

    Two requests are not retried as they were sent:

    - ``commit()`` without offsets would commit the new instance's
      positions, which hold nothing fetched, so it raises
      :class:`CommitLostError` instead.
    - A subscribed instance gets its partitions at its first fetch, so a
      seek or a commit with offsets retried on a new subscribed instance is
      refused with 409 (40903) until the instance has fetched.

    If the instance is created again but subscribing or assigning fails,
    the next request tries again before it is sent.

    Errors raise :class:`~diaspora_event_sdk.sdk.web_client.WebAPIError`,
    whose ``error_code`` is the service's code. The web client retries
    429, 500, 502, 503 and 504 replies, as globus-sdk does by default.

    The service serves an instance one request at a time, so use a
    ``RESTConsumer`` from one thread at a time. ``close()`` may be called
    from another thread; a request that then finds the instance gone
    raises instead of creating it again.
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
        :raises ValueError: If the service gives an instance URL whose scheme
            or host differs from the client's base URL; the consumer sends
            the client's token to no other host.
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
        # Held while the instance is created again or closed, so that two
        # threads that find it gone create it once, and close() waits.
        self._lock = threading.Lock()
        # Counts creates, so a thread can tell that another thread has
        # already created the instance again.
        self._generation = 0
        # The instance was created again, but subscribing or assigning it
        # as before has not yet succeeded.
        self._replay_pending = False
        self._closing = False
        self._closed = False
        self.name: str | None = name
        self.base_uri = ""
        self._create()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *exc_info: object) -> None:
        if exc_type is None:
            self.close()
            return
        # A failing close would hide the error that ended the with block.
        try:
            self.close()
        except Exception:
            logger.warning("Failed to delete %r", self, exc_info=True)

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
        self._request("POST", "/subscription", data={"topics": names}, replay=False)
        self._set_state(names, [])

    def subscription(self) -> list[str]:
        """Return the topics the instance is subscribed to."""
        return list(self._request("GET", "/subscription").data["topics"])

    def unsubscribe(self) -> None:
        """Unsubscribe from every topic, and drop any assigned partitions."""
        self._request("DELETE", "/subscription", replay=False)
        self._set_state([], [])

    def assign(self, partitions: Iterable[TopicPartitionT]) -> None:
        """Assign partitions to the instance, in place of a subscription."""
        assigned = [(topic, partition) for topic, partition in partitions]
        self._request(
            "POST",
            "/assignments",
            data={"partitions": _partitions(assigned)},
            replay=False,
        )
        self._set_state([], assigned)

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
        "value"}`` whose values are bytes or None. A binary instance's keys
        and values are bytes; a json instance's are JSON values or str.

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
        binary = self.format == "binary"
        return [decode_record(record, binary=binary) for record in records]

    def commit(self, offsets: Mapping[TopicPartitionT, int] | None = None) -> None:
        """Commit offsets for the group.

        :param offsets: For each partition, the offset of the last record
            processed; the group commits the one after it. If not given,
            commits the position of each assigned partition, the record
            after the last one fetched.
        :raises CommitLostError: If ``offsets`` is not given and the
            instance was gone. Nothing was committed; the instance has been
            created again, and the next fetch resumes at the group's last
            commit.
        """
        if offsets is None:
            self._request("POST", "/offsets", positions=True)
        else:
            self._request("POST", "/offsets", data={"offsets": _offsets(offsets)})

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
        taken as deleted. Closing twice does nothing.

        ``close()`` may be called from a thread other than the one using
        the consumer. It waits while another thread creates the instance
        again.
        """
        with self._lock:
            if self._closed or self._closing:
                return
            self._closing = True
        try:
            self._send("DELETE", "")
        except WebAPIError as err:
            if not _instance_gone(err):
                self._closing = False
                raise
        self._closed = True

    def _set_state(self, topics: list[str], partitions: list[TopicPartitionT]) -> None:
        self._topics, self._partitions = topics, partitions
        self._replay_pending = False

    def _create(self) -> None:
        settings = dict(self._settings)
        if self.name is not None:
            settings["name"] = self.name
        group = urllib.parse.quote(self.group, safe="")
        url = f"{self._web.base_url.rstrip('/')}/api/v2/consumers/{group}"
        reply = self._web.post(
            url, data=settings, headers=self._headers(), encoding="json"
        )
        base_uri = reply.data["base_uri"]
        _check_same_origin(base_uri, self._web.base_url)
        self.name = reply.data["instance_id"]
        self.base_uri = base_uri
        self._generation += 1

    def _repair(self, gone: int | None, *, replay: bool) -> None:
        """Create the instance again if it is still the one found gone, and
        subscribe or assign it as before if ``replay`` and that is pending.

        :param gone: The generation of the instance that answered 40403, or
            None if no instance was found gone.
        """
        with self._lock:
            if self._closing or self._closed:
                raise RuntimeError(f"{self!r} is closed")
            if gone == self._generation:
                logger.info(
                    "Consumer instance %s of group %s is gone; creating it again",
                    self.name,
                    self.group,
                )
                self._create()
                self._replay_pending = bool(self._topics or self._partitions)
            if replay and self._replay_pending:
                if self._topics:
                    self._send("POST", "/subscription", data={"topics": self._topics})
                else:
                    self._send(
                        "POST",
                        "/assignments",
                        data={"partitions": _partitions(self._partitions)},
                    )
                self._replay_pending = False

    def _request(
        self,
        method: str,
        route: str,
        *,
        data: dict[str, t.Any] | None = None,
        query_params: dict[str, t.Any] | None = None,
        accept: str | None = None,
        replay: bool = True,
        positions: bool = False,
    ) -> globus_sdk.GlobusHTTPResponse:
        """Send a request, creating the instance again if it is gone.

        :param replay: Whether the request needs the instance subscribed or
            assigned as before; False for a request that replaces both.
        :param positions: Whether the request commits the instance's
            positions, which a new instance does not have, so that it is
            not retried.
        """
        if self._closed or self._closing:
            raise RuntimeError(f"{self!r} is closed")
        generation = self._generation
        try:
            if replay and self._replay_pending:
                self._repair(None, replay=True)
            return self._send(
                method, route, data=data, query_params=query_params, accept=accept
            )
        except WebAPIError as err:
            if not (self._recover and _instance_gone(err)):
                raise
            if self._closing or self._closed:
                raise
            self._repair(generation, replay=replay)
            if positions:
                raise CommitLostError(err._underlying_response) from err
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


def _check_same_origin(base_uri: str, base_url: str) -> None:
    uri, url = urllib.parse.urlsplit(base_uri), urllib.parse.urlsplit(base_url)
    if (uri.scheme, uri.netloc) != (url.scheme, url.netloc):
        raise ValueError(
            f"The service gave the instance URL {base_uri!r}, whose scheme or "
            f"host differs from the client's {url.scheme}://{url.netloc}; the "
            "consumer sends its token to no other host."
        )


def _instance_gone(err: WebAPIError) -> bool:
    return err.http_status == 404 and err.error_code == INSTANCE_NOT_FOUND


def _partitions(partitions: Iterable[TopicPartitionT]) -> list[dict[str, t.Any]]:
    return [{"topic": topic, "partition": partition} for topic, partition in partitions]


def _offsets(offsets: Mapping[TopicPartitionT, int]) -> list[dict[str, t.Any]]:
    return [
        {"topic": topic, "partition": partition, "offset": offset}
        for (topic, partition), offset in offsets.items()
    ]
