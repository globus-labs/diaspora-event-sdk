import json
from datetime import datetime, timedelta, timezone
from unittest import mock

import globus_sdk
import pytest
import requests
import responses
import urllib3

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
        ("text", {"type": "JSON", "data": "text"}),
        ('{"step": 1}', {"type": "JSON", "data": '{"step": 1}'}),
        (3, {"type": "JSON", "data": 3}),
        ([1, None], {"type": "JSON", "data": [1, None]}),
        (False, {"type": "JSON", "data": False}),
    ],
)
def test_produce_types_values_as_kafka_producer_does(client, http, value, encoded):
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


@pytest.mark.parametrize(
    ("key", "encoded"),
    [
        ("job-42", {"type": "STRING", "data": "job-42"}),
        (b"\x00", {"type": "BINARY", "data": "AA=="}),
        (7, {"type": "JSON", "data": 7}),
    ],
)
def test_produce_types_keys(client, http, key, encoded):
    http.post(RECORDS, json={})
    client.produce("t1", 1, key=key)
    assert body(http.calls[0])["key"] == encoded


def test_produce_takes_explicit_types(client, http):
    http.post(RECORDS, json={})
    client.produce("t1", "plain", key="42", value_type="STRING", key_type="JSON")
    client.produce("t1", b"raw", value_type="BINARY")
    assert body(http.calls[0]) == {
        "key": {"type": "JSON", "data": "42"},
        "value": {"type": "STRING", "data": "plain"},
    }
    assert body(http.calls[1]) == {"value": {"type": "BINARY", "data": "cmF3"}}


@pytest.mark.parametrize(
    ("value", "value_type"),
    [({"a": 1}, "STRING"), ("text", "BINARY"), (b"x", "JSON"), (1, "AVRO")],
)
def test_produce_refuses_a_value_its_type_cannot_hold(client, value, value_type):
    with pytest.raises((TypeError, ValueError)):
        client.produce("t1", value, value_type=value_type)


@pytest.mark.parametrize("header", [5, 1.5, ["a"], {"a": 1}])
def test_produce_refuses_a_header_value_of_another_type(client, header):
    with pytest.raises(TypeError, match="bytes, str or None"):
        client.produce("t1", 1, headers=[("h", header)])


@pytest.mark.parametrize(
    "records",
    [
        [{"value": 1}, {"id": "0", "value": 2}],
        [{"id": "a", "value": 1}, {"id": "a", "value": 2}],
    ],
)
def test_produce_batch_refuses_repeated_ids(client, records):
    with pytest.raises(ValueError, match="id '"):
        client.produce_batch("t1", records)


def test_produce_batch_takes_types(client, http):
    http.post(f"{RECORDS}:batch", status=207, json={"successes": [], "failures": []})
    client.produce_batch("t1", [{"value": "done", "value_type": "STRING"}])
    assert body(http.calls[0])["entries"] == [
        {"id": "0", "value": {"type": "STRING", "data": "done"}}
    ]


@pytest.fixture
def no_sleep():
    with mock.patch("time.sleep"):
        yield


@pytest.mark.parametrize(
    ("status", "code"), [(500, 50003), (500, 50002), (502, None), (504, None)]
)
def test_produce_does_not_retry_an_answer_after_a_send(
    client, http, no_sleep, status, code
):
    http.post(RECORDS, status=status, json={"error_code": code, "message": "x"})
    with pytest.raises(WebAPIError):
        client.produce("t1", 1)
    assert len(http.calls) == 1


@pytest.mark.parametrize(("status", "code"), [(429, 42901), (503, 50302)])
def test_produce_retries_a_refusal_before_any_send(
    client, http, no_sleep, status, code
):
    http.post(
        RECORDS,
        status=status,
        json={"error_code": code, "message": "x"},
        headers={"Retry-After": "1"},
    )
    http.post(RECORDS, json={"offset": 1})
    assert client.produce("t1", 1) == {"offset": 1}
    assert len(http.calls) == 2


def test_produce_batch_does_not_retry_a_500(client, http, no_sleep):
    http.post(f"{RECORDS}:batch", status=500, json={"error_code": 50003})
    with pytest.raises(WebAPIError):
        client.produce_batch("t1", [{"value": 1}])
    assert len(http.calls) == 1


def test_produce_does_not_retry_a_connection_lost_after_connecting(
    client, http, no_sleep
):
    http.post(RECORDS, body=requests.exceptions.ConnectionError("reset by peer"))
    with pytest.raises(globus_sdk.NetworkError):
        client.produce("t1", 1)
    assert len(http.calls) == 1


def test_produce_retries_a_connection_never_made(client, http, no_sleep):
    refused = urllib3.exceptions.NewConnectionError(None, "refused")
    http.post(
        RECORDS,
        body=requests.exceptions.ConnectionError(
            urllib3.exceptions.MaxRetryError(None, RECORDS, refused)
        ),
    )
    http.post(RECORDS, body=requests.exceptions.ConnectTimeout("connect timeout"))
    http.post(RECORDS, json={"offset": 2})
    assert client.produce("t1", 1) == {"offset": 2}
    assert len(http.calls) == 3


def test_other_calls_keep_globus_sdk_retries(client, http, no_sleep):
    url = f"{BASE}/api/v3/{NS}/t1"
    http.post(url, status=500, json={})
    http.post(url, json={"status": "success"})
    assert client.create_topic("t1") == {"status": "success"}
    assert len(http.calls) == 2
