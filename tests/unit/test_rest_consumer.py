import base64
import json
import threading
import time
from unittest import mock

import globus_sdk
import pytest
import responses

from diaspora_event_sdk import CommitLostError, RESTConsumer, WebAPIError
from diaspora_event_sdk.sdk.client import Client

BASE = "https://octopus.example"
SUBJECT = "0b8fa3a4-4f4e-4a8c-9c1d-1234567890ab"
CREATE_URL = f"{BASE}/api/v2/consumers/g1"
INSTANCE = f"{BASE}/api/v2/consumers/g1/instances/inst"
V2 = "application/vnd.kafka.v2+json"
GONE = {"error_code": 40403, "message": "Consumer instance not found."}


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


def created(http, name="inst", base_uri=INSTANCE):
    http.post(
        CREATE_URL,
        json={"instance_id": name, "base_uri": base_uri},
        content_type=V2,
    )


def gone(http, method, url):
    http.add(method, url, status=404, json=GONE, content_type=V2)


def refused(http, method, url, status, code):
    http.add(
        method,
        url,
        status=status,
        json={"error_code": code, "message": "refused"},
        content_type=V2,
    )


def body(call):
    return json.loads(call.request.body) if call.request.body else None


def routes(http):
    return [(c.request.method, c.request.url.split("?")[0]) for c in http.calls]


def b64(data):
    return base64.b64encode(data).decode()


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
    # base_uri is absolute and used as given, here at a path the client
    # would not build itself
    uri = f"{BASE}/elsewhere/instances/inst"
    created(http, base_uri=uri)
    http.post(f"{uri}/subscription", status=204)
    http.get(f"{uri}/subscription", json={"topics": ["t1"]}, content_type=V2)
    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["t1"])
    assert consumer.subscription() == ["t1"]
    assert body(http.calls[1]) == {"topics": ["t1"]}
    assert http.calls[1].request.headers["Content-Type"] == V2
    assert http.calls[1].request.headers["Authorization"] == "Bearer token"


@pytest.mark.parametrize(
    "uri",
    [
        "http://octopus.example/api/v2/consumers/g1/instances/inst",
        "https://elsewhere.example/api/v2/consumers/g1/instances/inst",
        "https://octopus.example:8443/api/v2/consumers/g1/instances/inst",
    ],
)
def test_base_uri_of_another_origin_is_refused(client, http, uri):
    created(http, base_uri=uri)
    with pytest.raises(ValueError, match="no other host"):
        RESTConsumer("g1", client=client)
    assert len(http.calls) == 1  # nothing was sent to the other origin


def test_subscribe_takes_one_topic_name(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    RESTConsumer("g1", client=client).subscribe("t1")
    assert body(http.calls[1]) == {"topics": ["t1"]}


def test_fetch_json_sends_accept_and_decodes_headers(client, http):
    created(http)
    http.get(
        f"{INSTANCE}/records",
        json=[
            {
                "topic": "t1",
                "key": "k",
                "value": {"step": 7},
                "partition": 0,
                "offset": 3,
                "headers": [
                    {"name": "trace", "value": "AAE="},
                    {"name": "none", "value": None},
                ],
            }
        ],
        content_type="application/vnd.kafka.json.v2+json",
    )
    consumer = RESTConsumer("g1", client=client, format="json")
    (record,) = consumer.fetch(timeout_ms=1000, max_bytes=500)
    assert record["key"] == "k"
    assert record["value"] == {"step": 7}
    assert record["headers"] == [
        {"name": "trace", "value": b"\x00\x01"},
        {"name": "none", "value": None},
    ]
    request = http.calls[1].request
    assert request.headers["Accept"] == "application/vnd.kafka.json.v2+json"
    assert "timeout=1000" in request.url
    assert "max_bytes=500" in request.url


def test_fetch_binary_decodes_base64(client, http):
    created(http)
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

    assert routes(http) == [
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
    refused(http, "GET", f"{INSTANCE}/records", status, code)
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


def test_commit_without_offsets_on_a_gone_instance_raises(client, http):
    # The retried commit would commit the new instance's positions, which
    # hold nothing, and answer 200 []: the commit would be lost silently.
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    gone(http, "POST", f"{INSTANCE}/offsets")
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    http.get(f"{INSTANCE}/records", json=[], content_type=V2)

    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["t1"])
    with pytest.raises(CommitLostError) as info:
        consumer.commit()
    assert isinstance(info.value, WebAPIError)
    assert info.value.error_code == 40403
    assert "nothing was committed" in str(info.value)
    # recreated and subscribed again, and the commit not sent again
    assert routes(http)[3:] == [
        ("POST", CREATE_URL),
        ("POST", f"{INSTANCE}/subscription"),
    ]
    consumer.fetch()  # the consumer stays usable
    assert routes(http)[-1] == ("GET", f"{INSTANCE}/records")


def test_commit_with_offsets_on_a_gone_instance_is_retried(client, http):
    created(http)
    http.post(f"{INSTANCE}/assignments", status=204)
    gone(http, "POST", f"{INSTANCE}/offsets")
    created(http)
    http.post(f"{INSTANCE}/assignments", status=204)
    http.post(f"{INSTANCE}/offsets", json=[], content_type=V2)
    consumer = RESTConsumer("g1", client=client)
    consumer.assign([("t1", 0)])
    consumer.commit({("t1", 0): 9})
    assert body(http.calls[-1]) == {
        "offsets": [{"topic": "t1", "partition": 0, "offset": 9}]
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


def test_unsubscribe_forgets_the_assignment(client, http):
    # The service's unsubscribe also drops an assignment, so recovery must
    # not assign the partitions again before a later subscribe.
    created(http)
    http.post(f"{INSTANCE}/assignments", status=204)
    http.delete(f"{INSTANCE}/subscription", status=204)
    gone(http, "POST", f"{INSTANCE}/subscription")
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    consumer = RESTConsumer("g1", client=client)
    consumer.assign([("t1", 0)])
    consumer.unsubscribe()
    consumer.subscribe(["t2"])
    assert routes(http)[3:] == [
        ("POST", f"{INSTANCE}/subscription"),
        ("POST", CREATE_URL),
        ("POST", f"{INSTANCE}/subscription"),
    ]
    assert body(http.calls[-1]) == {"topics": ["t2"]}


@pytest.mark.parametrize(
    ("call", "route"),
    [
        (lambda c: c.subscribe(["new"]), ("POST", "/subscription")),
        (lambda c: c.assign([("new", 0)]), ("POST", "/assignments")),
        (lambda c: c.unsubscribe(), ("DELETE", "/subscription")),
    ],
)
def test_a_call_that_replaces_the_subscription_is_not_preceded_by_it(
    client, http, call, route
):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["old"])
    method, path = route
    gone(http, method, f"{INSTANCE}{path}")
    created(http)
    http.add(method, f"{INSTANCE}{path}", status=204)
    call(consumer)
    # recreated, then the call alone: no subscribe to "old" first
    assert routes(http)[2:] == [
        (method, f"{INSTANCE}{path}"),
        ("POST", CREATE_URL),
        (method, f"{INSTANCE}{path}"),
    ]


def test_failed_resubscribe_is_tried_again_by_the_next_call(client, http):
    created(http)
    http.post(f"{INSTANCE}/subscription", status=204)
    gone(http, "GET", f"{INSTANCE}/records")
    created(http)
    refused(http, "POST", f"{INSTANCE}/subscription", 503, 50302)
    consumer = RESTConsumer("g1", client=client)
    consumer.subscribe(["t1"])
    with (
        mock.patch("time.sleep"),
        mock.patch.object(client.web_client.retry_config, "max_retries", 0),
        pytest.raises(WebAPIError) as info,
    ):
        consumer.fetch()
    assert info.value.error_code == 50302
    http.replace("POST", f"{INSTANCE}/subscription", status=204)
    http.get(f"{INSTANCE}/records", json=[], content_type=V2)
    consumer.fetch()
    assert routes(http)[-2:] == [
        ("POST", f"{INSTANCE}/subscription"),
        ("GET", f"{INSTANCE}/records"),
    ]
    assert body(http.calls[-2]) == {"topics": ["t1"]}


def test_a_call_racing_close_does_not_recreate(client):
    # The DELETE of close() lands before a fetch from another thread, which
    # then finds the instance gone and must not create it again.
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        created(http)
        consumer = RESTConsumer("g1", client=client)
        deleting = threading.Event()

        def fetch(request):
            deleting.wait(5)
            return (404, {"Content-Type": V2}, json.dumps(GONE))

        def delete(request):
            deleting.set()
            time.sleep(0.2)  # the fetch's 404 arrives while closing
            return (204, {}, "")

        http.add_callback("GET", f"{INSTANCE}/records", callback=fetch)
        http.add_callback("DELETE", INSTANCE, callback=delete)
        errors = []

        def run():
            try:
                consumer.fetch(timeout_ms=1)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        thread = threading.Thread(target=run)
        thread.start()
        time.sleep(0.05)
        consumer.close()
        thread.join()
        creates = [r for r in routes(http) if r == ("POST", CREATE_URL)]
    assert consumer.closed
    assert len(creates) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], WebAPIError)
    assert errors[0].error_code == 40403


def test_two_threads_that_find_the_instance_gone_create_it_once(client):
    with responses.RequestsMock() as http:
        created(http)
        consumer = RESTConsumer("g1", client=client)
        both = threading.Barrier(2)
        seen = {"subscription": 0, "assignments": 0}

        def first_gone(route, payload):
            def reply(request):
                seen[route] += 1
                if seen[route] == 1:
                    both.wait(5)
                    return (404, {"Content-Type": V2}, json.dumps(GONE))
                return (200, {"Content-Type": V2}, json.dumps(payload))

            return reply

        http.add_callback(
            "GET",
            f"{INSTANCE}/subscription",
            callback=first_gone("subscription", {"topics": []}),
        )
        http.add_callback(
            "GET",
            f"{INSTANCE}/assignments",
            callback=first_gone("assignments", {"partitions": []}),
        )
        creates = []

        def create(request):
            creates.append(request)
            if len(creates) > 1:
                return (409, {"Content-Type": V2}, json.dumps({"error_code": 40902}))
            return (
                200,
                {"Content-Type": V2},
                json.dumps({"instance_id": "inst", "base_uri": INSTANCE}),
            )

        http.add_callback("POST", CREATE_URL, callback=create)
        out = {}

        def run(name, call):
            try:
                out[name] = call()
            except Exception as e:  # noqa: BLE001
                out[name] = e

        threads = [
            threading.Thread(target=run, args=("sub", consumer.subscription)),
            threading.Thread(target=run, args=("asg", consumer.assignment)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert out == {"sub": [], "asg": []}
    assert len(creates) == 1


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


def test_a_failing_close_does_not_hide_the_with_blocks_error(client, http):
    created(http)
    refused(http, "DELETE", INSTANCE, 409, 40904)

    class Stop(Exception):
        pass

    with pytest.raises(Stop), RESTConsumer("g1", client=client):
        raise Stop


def test_close_takes_a_gone_instance_as_deleted(client, http):
    created(http)
    gone(http, "DELETE", INSTANCE)
    consumer = RESTConsumer("g1", client=client)
    consumer.close()
    assert consumer.closed
    assert len(http.calls) == 2


def test_close_raises_other_errors(client, http):
    created(http)
    refused(http, "DELETE", INSTANCE, 409, 40904)
    consumer = RESTConsumer("g1", client=client)
    with pytest.raises(WebAPIError):
        consumer.close()
    assert not consumer.closed
