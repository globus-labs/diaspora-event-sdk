"""Records in the body forms of the web service's REST routes."""

from __future__ import annotations

import base64
import typing as t
from collections.abc import Iterable, Mapping
from datetime import datetime

HeadersT = Mapping[str, bytes | str | None] | Iterable[tuple[str, bytes | str | None]]
DataTypeT = t.Literal["BINARY", "JSON", "STRING"]

_BYTES = (bytes, bytearray, memoryview)


def _b64encode(data: bytes | bytearray | memoryview) -> str:
    return base64.b64encode(bytes(data)).decode("ascii")


def encode_data(
    data: t.Any, data_type: DataTypeT | None, *, str_type: DataTypeT
) -> dict[str, t.Any]:
    """Give a key or value as Confluent's REST API v3 ``{"type", "data"}``.

    Without ``data_type``, bytes are sent as BINARY, a str as ``str_type``
    and any other value as JSON. BINARY takes bytes, STRING a str, and JSON
    any value that JSON can encode.
    """
    if data_type is None:
        if isinstance(data, _BYTES):
            data_type = "BINARY"
        elif isinstance(data, str):
            data_type = str_type
        else:
            data_type = "JSON"
    if data_type == "BINARY":
        if not isinstance(data, _BYTES):
            raise TypeError(f"BINARY data must be bytes, not {type(data).__name__}")
        return {"type": "BINARY", "data": _b64encode(data)}
    if data_type == "STRING":
        if not isinstance(data, str):
            raise TypeError(f"STRING data must be a str, not {type(data).__name__}")
        return {"type": "STRING", "data": data}
    if data_type == "JSON":
        if isinstance(data, _BYTES):
            raise TypeError("JSON data cannot be bytes; send bytes as BINARY")
        return {"type": "JSON", "data": data}
    raise ValueError(f"type must be BINARY, JSON or STRING, not {data_type!r}")


def encode_headers(headers: HeadersT) -> list[dict[str, str | None]]:
    """Give headers as ``[{"name", "value"}]``, each value in base64 or None.

    A str value is sent as its UTF-8 bytes.
    """
    items = headers.items() if isinstance(headers, Mapping) else headers
    encoded: list[dict[str, str | None]] = []
    for name, value in items:
        if isinstance(value, str):
            value = value.encode("utf-8")
        if value is not None and not isinstance(value, _BYTES):
            raise TypeError(
                f"header {name!r} must be bytes, str or None, "
                f"not {type(value).__name__}"
            )
        encoded.append(
            {"name": name, "value": None if value is None else _b64encode(value)}
        )
    return encoded


def encode_record(
    value: t.Any = None,
    key: t.Any = None,
    headers: HeadersT | None = None,
    timestamp: datetime | str | None = None,
    *,
    value_type: DataTypeT | None = None,
    key_type: DataTypeT | None = None,
) -> dict[str, t.Any]:
    """Give a record in the body form of Confluent's REST API v3.

    A value that is a str is sent as JSON, a JSON string, and a key that
    is a str as STRING, plain text; ``value_type`` and ``key_type`` choose
    otherwise. A key or value of None is left out, and so are absent
    headers and timestamp. A datetime timestamp must carry a UTC offset.
    """
    record: dict[str, t.Any] = {}
    if key is not None:
        record["key"] = encode_data(key, key_type, str_type="STRING")
    if value is not None:
        record["value"] = encode_data(value, value_type, str_type="JSON")
    if headers is not None:
        record["headers"] = encode_headers(headers)
    if isinstance(timestamp, datetime):
        if timestamp.utcoffset() is None:
            raise ValueError("timestamp must carry a UTC offset (tzinfo)")
        record["timestamp"] = timestamp.isoformat()
    elif timestamp is not None:
        record["timestamp"] = timestamp
    return record


def decode_record(record: dict[str, t.Any], *, binary: bool) -> dict[str, t.Any]:
    """Decode a fetched record's header values, which are base64 in both
    formats, into bytes, and a binary instance's key and value too. A null
    one stays None."""
    decoded = dict(record)
    if binary:
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
