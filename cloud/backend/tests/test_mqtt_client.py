"""MQTT connection lifecycle and recovery tests."""
from app.services import mqtt_client


class FakeMqttClient:
    def __init__(self):
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.connect_args = None
        self.connect_async_args = None
        self.reconnect_delays = None
        self.loop_started = False
        self.subscriptions = []

    def reconnect_delay_set(self, min_delay, max_delay):
        self.reconnect_delays = (min_delay, max_delay)

    def connect(self, host, port, keepalive):
        self.connect_args = (host, port, keepalive)

    def connect_async(self, host, port, keepalive):
        self.connect_async_args = (host, port, keepalive)

    def loop_start(self):
        self.loop_started = True

    def loop_stop(self):
        self.loop_started = False

    def disconnect(self):
        return None

    def is_connected(self):
        return False

    def subscribe(self, topic):
        self.subscriptions.append(topic)


def test_init_starts_async_connection_and_configures_backoff(monkeypatch):
    fake = FakeMqttClient()
    monkeypatch.setattr(mqtt_client.mqtt, "Client", lambda **kwargs: fake)
    monkeypatch.setattr(mqtt_client, "_client", None)
    monkeypatch.setattr(mqtt_client, "_subscribers", {})

    mqtt_client.init_mqtt()

    assert fake.on_disconnect is mqtt_client.on_disconnect
    assert fake.reconnect_delays == (1, 30)
    assert fake.connect_async_args == (
        mqtt_client.MQTT_BROKER,
        mqtt_client.MQTT_TLS_PORT if mqtt_client.MQTT_USE_TLS else mqtt_client.MQTT_PORT,
        60,
    )
    assert fake.connect_args is None
    assert fake.loop_started is True
    assert mqtt_client.get_mqtt_status()["started"] is True


def test_disconnect_marks_mqtt_unavailable(monkeypatch):
    monkeypatch.setattr(mqtt_client, "_connection_state", mqtt_client.MqttConnectionState())

    mqtt_client.on_disconnect(FakeMqttClient(), None, 7)

    status = mqtt_client.get_mqtt_status()
    assert status["connected"] is False
    assert status["reconnect_count"] == 1
    assert status["last_disconnected_at"] is not None
    assert status["last_error"] == "unexpected_disconnect_rc_7"


def test_recovery_marks_connected_and_restores_subscriptions(monkeypatch):
    fake = FakeMqttClient()
    monkeypatch.setattr(mqtt_client, "_connection_state", mqtt_client.MqttConnectionState())
    monkeypatch.setattr(mqtt_client, "_subscribers", {"home/#": []})

    mqtt_client.on_disconnect(fake, None, 7)
    mqtt_client.on_connect(fake, None, {}, 0)

    status = mqtt_client.get_mqtt_status()
    assert status["connected"] is True
    assert status["last_connected_at"] is not None
    assert status["last_error"] is None
    assert fake.subscriptions == ["home/#"]


def test_failed_connack_keeps_mqtt_unavailable(monkeypatch):
    monkeypatch.setattr(mqtt_client, "_connection_state", mqtt_client.MqttConnectionState())

    mqtt_client.on_connect(FakeMqttClient(), None, {}, 5)

    status = mqtt_client.get_mqtt_status()
    assert status["connected"] is False
    assert status["last_error"] == "connection_refused_rc_5"
