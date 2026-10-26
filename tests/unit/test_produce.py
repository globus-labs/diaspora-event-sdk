import json
from datetime import datetime, timedelta, timezone
from unittest import mock

import globus_sdk
import pytest
import responses

from diaspora_event_sdk import WebAPIError
from diaspora_event_sdk.sdk.client import Client

BASE = "https://octopus.example"
NS = "ns-1234567890ab"
SUBJECT = "0b8fa3a4-4f4e-4a8c-9c1d-1234567890ab"
RECORDS = f"{BASE}/api/v3/{NS}/topics/t1/records"


@pytest.fixture
def client():
    with (
        mock.patch.object(Client, "_resolve_identity"),
        mock.patch(
            "diaspora_event_sdk.sdk.client.get_web_service_url",
            return_value=f"{BASE}/",
        ),
    ):
        c = Client(authorizer=globus_sdk.AccessTokenAuthorizer("token"))
    c.subject_openid = SUBJECT
    c.namespace = NS
    return c


@pytest.fixture
def http():
    with responses.RequestsMock() as rsps:
        yield rsps


def body(call):
    return json.loads(call.request.body)


def test_produce_sends_one_record(client, http):
    reply = {
        "topic_name": "t1",
        "partition_id": 0,
        "offset": 12,
        "timestamp": "2026-10-26T15:04:05.123Z",
    }
    http.post(RECORDS, json=reply)
    result = client.produce(
        "t1",
        {"step": 7},
        key="job-42",
        headers=[("trace", b"\x00\x01"), ("note", "hi"), ("empty", None)],
        timestamp=datetime(2026, 10, 26, 15, 4, 5, tzinfo=timezone.utc),
    )
    assert result == reply
    request = http.calls[0].request
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Subject"] == SUBJECT
    assert request.headers["Authorization"] == "Bearer token"
    assert body(http.calls[0]) == {
        "key": {"type": "STRING", "data": "job-42"},
        "value": {"type": "JSON", "data": {"step": 7}},
        "headers": [
            {"name": "trace", "value": "AAE="},
            {"name": "note", "value": "aGk="},
            {"name": "empty", "value": None},
        ],
        "timestamp": "2026-10-26T15:04:05+00:00",
    }


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        (b"\xff", {"type": "BINARY", "data": "/w=="}),
        (bytearray(b"ab"), {"type": "BINARY", "data": "YWI="}),
        ("text", {"type": "STRING", "data": "text"}),
        (3, {"type": "JSON", "data": 3}),
        ([1, None], {"type": "JSON", "data": [1, None]}),
        (False, {"type": "JSON", "data": False}),
    ],
)
def test_produce_types_values(client, http, value, encoded):
    http.post(RECORDS, json={})
    client.produce("t1", value)
    assert body(http.calls[0]) == {"value": encoded}


def test_produce_takes_another_namespace_and_header_mapping(client, http):
    url = f"{BASE}/api/v3/ns-other/topics/t1/records"
    http.post(url, json={})
    client.produce("t1", key=b"k", headers={"a": b"b"}, namespace="ns-other")
    assert body(http.calls[0]) == {
        "key": {"type": "BINARY", "data": "aw=="},
        "headers": [{"name": "a", "value": "Yg=="}],
    }


def test_produce_refuses_a_naive_timestamp(client):
    with pytest.raises(ValueError, match="UTC offset"):
        client.produce("t1", 1, timestamp=datetime(2026, 10, 26))  # noqa: DTZ001


def test_produce_keeps_a_string_timestamp_and_offset(client, http):
    http.post(RECORDS, json={})
    client.produce(
        "t1",
        1,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone(timedelta(hours=-5))),
    )
    client.produce("t1", 1, timestamp="2026-10-26T15:04:05.123Z")
    assert body(http.calls[0])["timestamp"] == "2026-01-02T00:00:00-05:00"
    assert body(http.calls[1])["timestamp"] == "2026-10-26T15:04:05.123Z"


def test_produce_error_has_the_error_code(client, http):
    http.post(
        RECORDS,
        status=422,
        json={"error_code": 42206, "message": "needs a schema registry"},
    )
    with pytest.raises(WebAPIError) as info:
        client.produce("t1", 1)
    assert info.value.http_status == 422
    assert info.value.error_code == 42206


def test_produce_batch_returns_the_207_reply(client, http):
    reply = {
        "successes": [
            {
                "id": "0",
                "topic_name": "t1",
                "partition_id": 0,
                "offset": 13,
                "timestamp": "2026-10-26T15:04:05.456Z",
            }
        ],
        "failures": [
            {"id": "job-2", "error_code": 41302, "message": "record too large"}
        ],
    }
    http.post(f"{RECORDS}:batch", status=207, json=reply)
    result = client.produce_batch(
        "t1",
        [{"value": {"step": 8}}, {"id": "job-2", "value": b"x", "key": "k"}],
    )
    assert result == reply
    # the colon reaches the service as is, not percent-encoded
    assert http.calls[0].request.url == f"{RECORDS}:batch"
    assert body(http.calls[0]) == {
        "entries": [
            {"id": "0", "value": {"type": "JSON", "data": {"step": 8}}},
            {
                "id": "job-2",
                "key": {"type": "STRING", "data": "k"},
                "value": {"type": "BINARY", "data": "eA=="},
            },
        ]
    }


def test_produce_batch_refuses_unknown_fields(client):
    with pytest.raises(TypeError):
        client.produce_batch("t1", [{"vale": 1}])


def test_topic_names_are_quoted(client, http):
    http.post(f"{BASE}/api/v3/{NS}/topics/a%2Fb/records", json={})
    client.produce("a/b", 1)
    assert len(http.calls) == 1
