"""
MQTT client helpers for backend publish/subscribe.
"""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.config import (
    MQTT_BROKER,
    MQTT_CA_CERTS,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_TLS_PORT,
    MQTT_USERNAME,
    MQTT_USE_TLS,
)

logger = logging.getLogger(__name__)

_client: Optional[mqtt.Client] = None
_subscribers: dict[str, list[Callable]] = {}


@dataclass
class MqttConnectionState:
    started: bool = False
    connected: bool = False
    reconnect_count: int = 0
    last_connected_at: Optional[str] = None
    last_disconnected_at: Optional[str] = None
    last_error: Optional[str] = None


_connection_state = MqttConnectionState()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_mqtt_status() -> dict[str, object]:
    """Return a serializable snapshot of the MQTT connection state."""
    return asdict(_connection_state)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        _connection_state.connected = True
        _connection_state.last_connected_at = _utc_now()
        _connection_state.last_error = None
        logger.info("MQTT connected to %s:%s", MQTT_BROKER, MQTT_PORT)
        for topic in _subscribers:
            client.subscribe(topic)
            logger.info("MQTT subscribed: %s", topic)
    else:
        _connection_state.connected = False
        _connection_state.last_error = f"connection_refused_rc_{rc}"
        logger.error("MQTT connection failed, rc=%s", rc)


def on_disconnect(client, userdata, rc):
    """Track availability while Paho's network loop handles reconnection."""
    _connection_state.connected = False
    _connection_state.last_disconnected_at = _utc_now()
    if rc != 0:
        _connection_state.reconnect_count += 1
        _connection_state.last_error = f"unexpected_disconnect_rc_{rc}"
        logger.warning("MQTT disconnected unexpectedly, rc=%s; waiting for reconnect", rc)
    else:
        logger.info("MQTT disconnected")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        payload = msg.payload.decode("utf-8")

    logger.debug("MQTT received: %s -> %s", topic, payload)

    for pattern, callbacks in _subscribers.items():
        if _topic_match(pattern, topic):
            for callback in callbacks:
                try:
                    callback(topic, payload)
                except Exception as exc:
                    logger.error("MQTT callback failed: %s", exc)


def _topic_match(pattern: str, topic: str) -> bool:
    if pattern == "#":
        return True
    if pattern.endswith("/#"):
        return topic.startswith(pattern[:-2])
    return pattern == topic


def init_mqtt():
    """Initialize and connect the shared MQTT client."""
    global _client
    _client = mqtt.Client(client_id="smart-home-backend", protocol=mqtt.MQTTv311)
    _client.on_connect = on_connect
    _client.on_disconnect = on_disconnect
    _client.on_message = on_message

    if MQTT_USERNAME:
        _client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_USE_TLS:
        if MQTT_CA_CERTS:
            _client.tls_set(ca_certs=MQTT_CA_CERTS)
        else:
            _client.tls_set()

    port = MQTT_TLS_PORT if MQTT_USE_TLS else MQTT_PORT
    try:
        _client.reconnect_delay_set(min_delay=1, max_delay=30)
        _client.connect_async(MQTT_BROKER, port, keepalive=60)
        _client.loop_start()
        _connection_state.started = True
        _connection_state.connected = False
        _connection_state.last_error = None
        logger.info("MQTT client started at %s:%s", MQTT_BROKER, port)
    except Exception as exc:
        _connection_state.started = False
        _connection_state.connected = False
        _connection_state.last_error = str(exc)
        logger.warning("MQTT client failed to start: %s", exc)


def subscribe(topic: str, callback: Callable):
    """Register a callback for a topic pattern."""
    if topic not in _subscribers:
        _subscribers[topic] = []
        if _client and _client.is_connected():
            _client.subscribe(topic)
    _subscribers[topic].append(callback)


def publish_message(topic: str, payload: str, qos: int = 1):
    """Publish a message or raise if MQTT is unavailable."""
    if _client and _client.is_connected():
        _client.publish(topic, payload, qos=qos)
        logger.debug("MQTT published: %s -> %s", topic, payload)
        return

    logger.warning("MQTT not connected, dropping message: %s", topic)
    raise RuntimeError("mqtt_not_connected")


def stop_mqtt():
    """Stop the shared MQTT client."""
    global _client
    if _client:
        _client.loop_stop()
        _client.disconnect()
        _client = None
    _connection_state.started = False
    _connection_state.connected = False
