"""Records in the body forms of the web service's REST routes."""

from __future__ import annotations

import base64
import typing as t
from collections.abc import Iterable, Mapping
from datetime import datetime

HeadersT = Mapping[str, bytes | str | None] | Iterable[tuple[str, bytes | str | None]]


def _b64encode(data: bytes | bytearray | memoryview) -> str:
    return base64.b64encode(bytes(data)).decode("ascii")


def encode_data(data: t.Any) -> dict[str, t.Any]:
    """Give a key or value as Confluent's REST API v3 ``{"type", "data"}``.

    Bytes are sent as BINARY, a str as STRING, and any other value as JSON.
    """
    if isinstance(data, bytes | bytearray | memoryview):
        return {"type": "BINARY", "data": _b64encode(data)}
    if isinstance(data, str):
        return {"type": "STRING", "data": data}
    return {"type": "JSON", "data": data}


def encode_headers(headers: HeadersT) -> list[dict[str, str | None]]:
    """Give headers as ``[{"name", "value"}]``, each value in base64 or None."""
    items = headers.items() if isinstance(headers, Mapping) else headers
    encoded: list[dict[str, str | None]] = []
    for name, value in items:
        if isinstance(value, str):
            value = value.encode("utf-8")
        encoded.append(
            {"name": name, "value": None if value is None else _b64encode(value)}
        )
    return encoded


def encode_record(
    value: t.Any = None,
    key: t.Any = None,
    headers: HeadersT | None = None,
    timestamp: datetime | str | None = None,
) -> dict[str, t.Any]:
    """Give a record in the body form of Confluent's REST API v3.

    A key or value of None is left out, and so are absent headers and
    timestamp. A datetime timestamp must carry a UTC offset.
    """
    record: dict[str, t.Any] = {}
    if key is not None:
        record["key"] = encode_data(key)
    if value is not None:
        record["value"] = encode_data(value)
    if headers is not None:
        record["headers"] = encode_headers(headers)
    if isinstance(timestamp, datetime):
        if timestamp.utcoffset() is None:
            raise ValueError("timestamp must carry a UTC offset (tzinfo)")
        record["timestamp"] = timestamp.isoformat()
    elif timestamp is not None:
        record["timestamp"] = timestamp
    return record


def decode_binary_record(record: dict[str, t.Any]) -> dict[str, t.Any]:
    """Decode a binary instance's record: its key, value and header values
    become bytes, and a null one stays None."""
    decoded = dict(record)
    for field in ("key", "value"):
        if decoded.get(field) is not None:
            decoded[field] = base64.b64decode(decoded[field])
    if decoded.get("headers"):
        decoded["headers"] = [
            {
                **header,
                "value": None
                if header.get("value") is None
                else base64.b64decode(header["value"]),
            }
            for header in decoded["headers"]
        ]
    return decoded
