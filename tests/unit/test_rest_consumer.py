import base64
import json
from unittest import mock

import globus_sdk
import pytest
import responses

from diaspora_event_sdk import RESTConsumer, WebAPIError
from diaspora_event_sdk.sdk.client import Client

BASE = "https://octopus.example"
SUBJECT = "0b8fa3a4-4f4e-4a8c-9c1d-1234567890ab"
CREATE_URL = f"{BASE}/api/v2/consumers/g1"
# A host other than the client's: the consumer must use base_uri as given
INSTANCE = "https://instances.example/api/v2/consumers/g1/instances/inst"
V2 = "application/vnd.kafka.v2+json"


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
    c.namespace = "ns-1234567890ab"
    return c


@pytest.fixture
def http():
    with responses.RequestsMock() as rsps:
        yield rsps


def created(http, name="inst"):
    http.post(
        CREATE_URL,
        json={"instance_id": name, "base_uri": INSTANCE},
        content_type=V2,
    )


def gone(http, method, url):
    http.add(
        method,
        url,
        status=404,
        json={"error_code": 40403, "message": "Consumer instance not found."},
        content_type=V2,
    )


def body(call):
    return json.loads(call.request.body) if call.request.body else None


def test_create_sends_settings_and_auth(client, http):
    created(http)
    consumer = RESTConsumer(
        "g1",
        client=client,
        name="inst",
        format="json",
        auto_offset_reset="earliest",
        auto_commit_enable=False,
        fetch_min_bytes=1,
        consumer_request_timeout_ms=2000,
    )
    request = http.calls[0].request
    assert request.headers["Content-Type"] == V2
    assert request.headers["Subject"] == SUBJECT
    assert request.headers["Authorization"] == "Bearer token"
    assert body(http.calls[0]) == {
        "name": "inst",
        "format": "json",
        "auto.offset.reset": "earliest",
        "auto.commit.enable": "false",
        "fetch.min.bytes": 1,
        "consumer.request.timeout.ms": 2000,
    }
    assert consumer.name == "inst"
    assert consumer.base_uri == INSTANCE


def test_create_without_name_takes_the_service_name(client, http):
    created(http, name="a1b2c3d4e5f6")  # pragma: allowlist secret
    consumer = RESTConsumer("g1", client=client)
    assert body(http.calls[0]) == {"format": "binary"}
    assert consumer.name == "a1b2c3d4e5f6"  # pragma: allowlist secret


def test_requests_go_to_base_uri(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    http.get(f"{INSTANCE}/subscription", json={"topics": ["t1"]}, content_type=V2)
    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["t1"])
    assert consumer.subscription() == ["t1"]
    assert body(http.calls[1]) == {"topics": ["t1"]}
    assert http.calls[1].request.headers["Content-Type"] == V2
    assert http.calls[1].request.headers["Authorization"] == "Bearer token"


def test_subscribe_takes_one_topic_name(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    RESTConsumer("g1", client=client).subscribe("t1")
    assert body(http.calls[1]) == {"topics": ["t1"]}


def test_fetch_json_sends_accept_and_returns_records_as_given(client, http):
    created(http)
    records = [
        {
            "topic": "t1",
            "key": None,
            "value": {"step": 7},
            "partition": 0,
            "offset": 3,
            "headers": [{"name": "trace", "value": "AAE="}],
        }
    ]
    http.get(
        f"{INSTANCE}/records",
        json=records,
        content_type="application/vnd.kafka.json.v2+json",
    )
    consumer = RESTConsumer("g1", client=client, format="json")
    assert consumer.fetch(timeout_ms=1000, max_bytes=500) == records
    request = http.calls[1].request
    assert request.headers["Accept"] == "application/vnd.kafka.json.v2+json"
    assert "timeout=1000" in request.url
    assert "max_bytes=500" in request.url


def test_fetch_binary_decodes_base64(client, http):
    created(http)

    def b64(data):
        return base64.b64encode(data).decode()

    http.get(
        f"{INSTANCE}/records",
        json=[
            {
                "topic": "t1",
                "key": b64(b"k"),
                "value": b64(b"\x00\xff"),
                "partition": 0,
                "offset": 0,
                "headers": [
                    {"name": "a", "value": b64(b"\x01")},
                    {"name": "b", "value": None},
                ],
            },
            {
                "topic": "t1",
                "key": None,
                "value": None,
                "partition": 0,
                "offset": 1,
                "headers": [],
            },
        ],
        content_type="application/vnd.kafka.binary.v2+json",
    )
    consumer = RESTConsumer("g1", client=client)
    first, second = consumer.fetch()
    assert http.calls[1].request.headers["Accept"] == (
        "application/vnd.kafka.binary.v2+json"
    )
    assert first["key"] == b"k"
    assert first["value"] == b"\x00\xff"
    assert first["headers"] == [
        {"name": "a", "value": b"\x01"},
        {"name": "b", "value": None},
    ]
    assert second["key"] is None
    assert second["value"] is None


def test_fetch_recovers_a_subscribed_instance(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    gone(http, "GET", f"{INSTANCE}/records")
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    http.get(f"{INSTANCE}/records", json=[], content_type=V2)

    consumer = RESTConsumer(
        "g1", client=client, name="inst", auto_offset_reset="earliest"
    )
    consumer.subscribe(["t1", "t2"])
    assert consumer.fetch() == []

    urls = [(c.request.method, c.request.url.split("?")[0]) for c in http.calls]
    assert urls == [
        ("POST", CREATE_URL),
        ("POST", f"{INSTANCE}/subscription"),
        ("GET", f"{INSTANCE}/records"),
        ("POST", CREATE_URL),
        ("POST", f"{INSTANCE}/subscription"),
        ("GET", f"{INSTANCE}/records"),
    ]
    assert body(http.calls[3]) == body(http.calls[0])
    assert body(http.calls[4]) == {"topics": ["t1", "t2"]}


def test_recovery_assigns_the_same_partitions(client, http):
    created(http)
    http.post(f"{INSTANCE}/assignments", status=204)
    gone(http, "POST", f"{INSTANCE}/positions")
    created(http)
    http.post(f"{INSTANCE}/assignments", status=204)
    http.post(f"{INSTANCE}/positions", status=204)

    consumer = RESTConsumer("g1", client=client)
    consumer.assign([("t1", 0)])
    consumer.seek({("t1", 0): 5})

    assert body(http.calls[4]) == {"partitions": [{"topic": "t1", "partition": 0}]}
    assert body(http.calls[5]) == {
        "offsets": [{"topic": "t1", "partition": 0, "offset": 5}]
    }


def test_recovery_retries_once(client, http):
    created(http)
    gone(http, "GET", f"{INSTANCE}/records")
    created(http)
    gone(http, "GET", f"{INSTANCE}/records")

    consumer = RESTConsumer("g1", client=client)
    with pytest.raises(WebAPIError) as info:
        consumer.fetch()
    assert info.value.error_code == 40403
    assert len(http.calls) == 4


def test_no_recovery_when_disabled(client, http):
    created(http)
    gone(http, "GET", f"{INSTANCE}/records")
    consumer = RESTConsumer("g1", client=client, recover=False)
    with pytest.raises(WebAPIError) as info:
        consumer.fetch()
    assert info.value.error_code == 40403
    assert len(http.calls) == 2


@pytest.mark.parametrize(
    ("status", "code"),
    [(404, 40401), (404, 40402), (409, 40903), (406, 40601), (422, 42204)],
)
def test_other_errors_are_not_retried(client, http, status, code):
    created(http)
    http.get(
        f"{INSTANCE}/records",
        status=status,
        json={"error_code": code, "message": "refused"},
        content_type=V2,
    )
    consumer = RESTConsumer("g1", client=client)
    with pytest.raises(WebAPIError) as info:
        consumer.fetch()
    assert info.value.http_status == status
    assert info.value.error_code == code
    assert info.value.message == "refused"
    assert len(http.calls) == 2


def test_commit_with_and_without_offsets(client, http):
    created(http)
    http.post(f"{INSTANCE}/offsets", json=[], content_type=V2)
    http.post(f"{INSTANCE}/offsets", json=[], content_type=V2)
    consumer = RESTConsumer("g1", client=client)
    consumer.commit()
    consumer.commit({("t1", 0): 41})
    assert http.calls[1].request.body is None
    assert body(http.calls[2]) == {
        "offsets": [{"topic": "t1", "partition": 0, "offset": 41}]
    }


def test_committed_returns_offsets_by_partition(client, http):
    created(http)
    http.get(
        f"{INSTANCE}/offsets",
        json={
            "offsets": [{"topic": "t1", "partition": 0, "offset": 42, "metadata": ""}]
        },
        content_type=V2,
    )
    consumer = RESTConsumer("g1", client=client)
    assert consumer.committed([("t1", 0), ("t2", 0)]) == {("t1", 0): 42}
    assert body(http.calls[1]) == {
        "partitions": [
            {"topic": "t1", "partition": 0},
            {"topic": "t2", "partition": 0},
        ]
    }


def test_assignment_and_seeks(client, http):
    created(http)
    http.get(
        f"{INSTANCE}/assignments",
        json={"partitions": [{"topic": "t1", "partition": 0}]},
        content_type=V2,
    )
    http.post(f"{INSTANCE}/positions/beginning", status=204)
    http.post(f"{INSTANCE}/positions/end", status=204)
    consumer = RESTConsumer("g1", client=client)
    assert consumer.assignment() == [("t1", 0)]
    consumer.seek_to_beginning([("t1", 0)])
    consumer.seek_to_end()
    assert body(http.calls[2]) == {"partitions": [{"topic": "t1", "partition": 0}]}
    assert body(http.calls[3]) == {"partitions": []}


def test_unsubscribe_forgets_the_topics(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    http.delete(f"{INSTANCE}/subscription", status=204)
    gone(http, "GET", f"{INSTANCE}/records")
    created(http)
    http.get(f"{INSTANCE}/records", json=[], content_type=V2)
    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["t1"])
    consumer.unsubscribe()
    consumer.fetch()
    # recreated without subscribing again
    assert [c.request.method for c in http.calls[-2:]] == ["POST", "GET"]


def test_context_manager_deletes_the_instance(client, http):
    created(http)
    http.delete(INSTANCE, status=204)
    with RESTConsumer("g1", client=client) as consumer:
        assert not consumer.closed
    assert consumer.closed
    assert http.calls[1].request.method == "DELETE"
    consumer.close()
    assert len(http.calls) == 2
    with pytest.raises(RuntimeError, match="closed"):
        consumer.fetch()


def test_close_takes_a_gone_instance_as_deleted(client, http):
    created(http)
    gone(http, "DELETE", INSTANCE)
    consumer = RESTConsumer("g1", client=client)
    consumer.close()
    assert consumer.closed
    assert len(http.calls) == 2


def test_close_raises_other_errors(client, http):
    created(http)
    http.delete(
        INSTANCE,
        status=409,
        json={"error_code": 40904, "message": "busy"},
        content_type=V2,
    )
    consumer = RESTConsumer("g1", client=client)
    with pytest.raises(WebAPIError):
        consumer.close()
    assert not consumer.closed
