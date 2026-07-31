import json
import logging
from types import SimpleNamespace

import pytest

import app.main as main_module
from app.services import mqtt_client


@pytest.fixture(autouse=True)
def isolate_mqtt_state():
    previous_client = mqtt_client._client
    previous_connected = getattr(mqtt_client, "_connected", False)
    previous_subscribers = {
        topic: list(callbacks)
        for topic, callbacks in mqtt_client._subscribers.items()
    }
    mqtt_client._client = None
    mqtt_client._connected = False
    mqtt_client._subscribers.clear()
    yield
    mqtt_client._client = previous_client
    mqtt_client._connected = previous_connected
    mqtt_client._subscribers.clear()
    mqtt_client._subscribers.update(previous_subscribers)


class FakeClient:
    def __init__(self, connected=False):
        self.connected = connected
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.reconnect_delays = []
        self.async_connections = []
        self.loop_starts = 0
        self.loop_stops = 0
        self.disconnects = 0
        self.subscriptions = []
        self.published = []
        self.publish_rc = mqtt_client.mqtt.MQTT_ERR_SUCCESS

    def reconnect_delay_set(self, min_delay, max_delay):
        self.reconnect_delays.append((min_delay, max_delay))

    def connect_async(self, host, port, keepalive):
        self.async_connections.append((host, port, keepalive))

    def loop_start(self):
        self.loop_starts += 1

    def loop_stop(self):
        self.loop_stops += 1

    def disconnect(self):
        self.disconnects += 1

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def publish(self, topic, payload, qos):
        self.published.append((topic, payload, qos))
        return SimpleNamespace(rc=self.publish_rc)

    def is_connected(self):
        return self.connected


def test_topic_match_respects_path_boundary():
    assert mqtt_client._topic_match("home/#", "home") is True
    assert mqtt_client._topic_match(
        "home/#", "home/livingroom/light/status"
    ) is True
    assert mqtt_client._topic_match("home/#", "homebrew/light/status") is False


def test_subscribe_deduplicates_callback_and_broker_subscription(
    real_mqtt_functions,
):
    client = FakeClient(connected=True)
    callback = lambda *_: None
    mqtt_client._client = client
    mqtt_client.on_connect(client, None, None, 0)

    real_mqtt_functions.subscribe("home/#", callback)
    real_mqtt_functions.subscribe("home/#", callback)

    assert mqtt_client._subscribers["home/#"] == [callback]
    assert client.subscriptions == ["home/#"]


def test_stop_clears_subscribers_and_client(real_mqtt_functions):
    client = FakeClient(connected=True)
    mqtt_client._client = client
    mqtt_client._subscribers["home/#"] = [lambda *_: None]

    real_mqtt_functions.stop_mqtt()

    assert mqtt_client._client is None
    assert mqtt_client._subscribers == {}
    assert client.loop_stops == 1
    assert client.disconnects == 1


def test_init_uses_async_connect_and_reconnect_backoff(
    real_mqtt_functions,
    monkeypatch,
):
    client = FakeClient()
    monkeypatch.setattr(mqtt_client.mqtt, "Client", lambda **_kwargs: client)

    real_mqtt_functions.init_mqtt()

    expected_port = (
        mqtt_client.MQTT_TLS_PORT
        if mqtt_client.MQTT_USE_TLS
        else mqtt_client.MQTT_PORT
    )
    assert mqtt_client._client is client
    assert client.on_connect is mqtt_client.on_connect
    assert client.on_disconnect is mqtt_client.on_disconnect
    assert client.on_message is mqtt_client.on_message
    assert client.reconnect_delays == [(1, 30)]
    assert client.async_connections == [
        (mqtt_client.MQTT_BROKER, expected_port, 60)
    ]
    assert client.loop_starts == 1


def test_each_successful_connect_resubscribes_registered_topics():
    client = FakeClient()
    mqtt_client._client = client
    mqtt_client._subscribers.update(
        {
            "home/#": [lambda *_: None],
            "alerts": [lambda *_: None],
        }
    )

    mqtt_client.on_connect(client, None, None, 0)
    mqtt_client.on_connect(client, None, None, 0)

    assert client.subscriptions == ["home/#", "alerts", "home/#", "alerts"]


def test_is_mqtt_connected_reflects_shared_client_state():
    assert mqtt_client.is_mqtt_connected() is False
    client = FakeClient(connected=False)
    mqtt_client._client = client
    assert mqtt_client.is_mqtt_connected() is False
    mqtt_client.on_connect(client, None, None, 0)
    assert mqtt_client.is_mqtt_connected() is True
    mqtt_client.on_disconnect(client, None, mqtt_client.mqtt.MQTT_ERR_CONN_LOST)
    assert mqtt_client.is_mqtt_connected() is False


def test_stale_client_callbacks_do_not_change_connection_state():
    current = FakeClient()
    stale = FakeClient()
    mqtt_client._client = current

    mqtt_client.on_connect(stale, None, None, 0)
    assert mqtt_client.is_mqtt_connected() is False
    mqtt_client.on_connect(current, None, None, 0)
    assert mqtt_client.is_mqtt_connected() is True
    mqtt_client.on_disconnect(stale, None, mqtt_client.mqtt.MQTT_ERR_CONN_LOST)
    assert mqtt_client.is_mqtt_connected() is True


def test_publish_rejects_non_success_paho_result(real_mqtt_functions):
    client = FakeClient(connected=True)
    client.publish_rc = mqtt_client.mqtt.MQTT_ERR_NO_CONN
    mqtt_client._client = client
    mqtt_client.on_connect(client, None, None, 0)

    with pytest.raises(RuntimeError, match="mqtt_publish_failed"):
        real_mqtt_functions.publish_message("home/light/command", "{}")

    assert client.published == [("home/light/command", "{}", 1)]


def test_publish_accepts_successful_paho_result(real_mqtt_functions):
    client = FakeClient(connected=True)
    mqtt_client._client = client
    mqtt_client.on_connect(client, None, None, 0)

    real_mqtt_functions.publish_message("home/light/command", "{}", qos=2)

    assert client.published == [("home/light/command", "{}", 2)]


@pytest.mark.parametrize(
    "raw_payload",
    [
        pytest.param(b"\xff", id="invalid_utf8"),
        pytest.param(b"{invalid-json", id="invalid_json"),
        pytest.param(b"[]", id="array_root"),
        pytest.param(b'"scalar"', id="scalar_root"),
        pytest.param(b"null", id="null_root"),
        pytest.param(b'{"value":NaN}', id="nan"),
        pytest.param(b'{"value":Infinity}', id="infinity"),
        pytest.param(b'{"value":1e999}', id="overflow_float"),
        pytest.param(
            b'{"value":' + (b"9" * 5000) + b"}",
            id="oversized_integer",
        ),
        pytest.param(
            b'{"value":' + (b"[" * 2000) + b"0" + (b"]" * 2000) + b"}",
            id="excessive_depth",
        ),
        pytest.param(
            b'{"values":[' + (b"0," * 10000) + b"0]}",
            id="too_many_nodes",
        ),
    ],
)
def test_invalid_or_non_object_payload_stops_before_business_processing(
    raw_payload,
    client,
    db,
    monkeypatch,
    caplog,
):
    callback_calls = []
    rule_calls = []
    websocket_calls = []
    before_sensor_rows = db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    before_status = db.execute(
        "SELECT status_json FROM devices WHERE id = 1"
    ).fetchone()["status_json"]

    def callback(topic, payload):
        callback_calls.append((topic, payload))
        main_module.on_mqtt_message(topic, payload)

    mqtt_client._subscribers["home/#"] = [callback]
    monkeypatch.setattr(
        main_module.rule_engine,
        "on_sensor_data",
        lambda *args: rule_calls.append(args),
    )
    monkeypatch.setattr(
        main_module.asyncio,
        "run_coroutine_threadsafe",
        lambda *args: websocket_calls.append(args),
    )
    message = SimpleNamespace(
        topic="home/livingroom/temperature_sensor/sensor",
        payload=raw_payload,
    )

    with caplog.at_level(logging.WARNING):
        mqtt_client.on_message(None, None, message)

    assert callback_calls == []
    assert rule_calls == []
    assert websocket_calls == []
    assert db.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0] == before_sensor_rows
    assert db.execute(
        "SELECT status_json FROM devices WHERE id = 1"
    ).fetchone()["status_json"] == before_status
    assert "ignored MQTT payload" in caplog.text


def test_valid_json_object_is_dispatched_to_matching_callback():
    calls = []
    mqtt_client._subscribers["home/#"] = [
        lambda topic, payload: calls.append((topic, payload))
    ]
    message = SimpleNamespace(
        topic="home/livingroom/light/status",
        payload=json.dumps({"power": "on"}).encode("utf-8"),
    )

    mqtt_client.on_message(None, None, message)

    assert calls == [
        ("home/livingroom/light/status", {"power": "on"})
    ]
