"""
MQTT client helpers for backend publish/subscribe.
"""
import json
import logging
import math
import threading
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
_connected = False
_subscribers: dict[str, list[Callable]] = {}
_state_lock = threading.RLock()
_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 10_000


def _parse_finite_float(raw_value: str) -> float:
    value = float(raw_value)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return value


def _reject_non_finite_constant(raw_value: str):
    raise ValueError(f"non-finite JSON constant: {raw_value}")


def _payload_within_structural_limits(payload: dict) -> bool:
    nodes = 1
    stack: list[tuple[dict | list, int]] = [(payload, 0)]

    while stack:
        value, depth = stack.pop()
        children = value.values() if isinstance(value, dict) else value
        nodes += len(value)
        if nodes > _MAX_JSON_NODES:
            return False

        child_depth = depth + 1
        for child in children:
            if isinstance(child, (dict, list)):
                if child_depth > _MAX_JSON_DEPTH:
                    return False
                stack.append((child, child_depth))

    return True


def on_connect(client, userdata, flags, rc):
    global _connected
    connected_now = rc == 0
    with _state_lock:
        if client is not _client:
            logger.debug("ignored MQTT connect callback from stale client")
            return
        _connected = connected_now
        topics = list(_subscribers) if connected_now else []

    if connected_now:
        port = MQTT_TLS_PORT if MQTT_USE_TLS else MQTT_PORT
        logger.info("MQTT connected to %s:%s", MQTT_BROKER, port)
        for topic in topics:
            client.subscribe(topic)
            logger.info("MQTT subscribed: %s", topic)
    else:
        logger.error("MQTT connection failed, rc=%s", rc)


def on_disconnect(client, userdata, rc):
    global _connected
    with _state_lock:
        if client is not _client:
            logger.debug("ignored MQTT disconnect callback from stale client")
            return
        _connected = False

    if rc == 0:
        logger.info("MQTT disconnected")
    else:
        logger.warning("MQTT connection lost, rc=%s", rc)


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        decoded = msg.payload.decode("utf-8")
        payload = json.loads(
            decoded,
            parse_float=_parse_finite_float,
            parse_constant=_reject_non_finite_constant,
        )
    except UnicodeDecodeError:
        logger.warning("ignored MQTT payload on %s: invalid UTF-8", topic)
        return
    except (ValueError, RecursionError):
        logger.warning("ignored MQTT payload on %s: invalid JSON", topic)
        return

    if not isinstance(payload, dict):
        logger.warning("ignored MQTT payload on %s: JSON object required", topic)
        return
    if not _payload_within_structural_limits(payload):
        logger.warning("ignored MQTT payload on %s: structural limits exceeded", topic)
        return

    logger.debug("MQTT received: %s -> %s", topic, payload)

    with _state_lock:
        callbacks = [
            callback
            for pattern, registered in _subscribers.items()
            if _topic_match(pattern, topic)
            for callback in registered
        ]
    for callback in callbacks:
        try:
            callback(topic, payload)
        except Exception as exc:
            logger.error("MQTT callback failed: %s", exc)


def _topic_match(pattern: str, topic: str) -> bool:
    if pattern == "#":
        return True
    if pattern.endswith("/#"):
        prefix = pattern[:-2]
        return topic == prefix or topic.startswith(f"{prefix}/")
    return pattern == topic


def init_mqtt():
    """Initialize and connect the shared MQTT client."""
    global _client, _connected
    client = mqtt.Client(client_id="smart-home-backend", protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_USE_TLS:
        if MQTT_CA_CERTS:
            client.tls_set(ca_certs=MQTT_CA_CERTS)
        else:
            client.tls_set()

    port = MQTT_TLS_PORT if MQTT_USE_TLS else MQTT_PORT
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    with _state_lock:
        _client = client
        _connected = False
    client.connect_async(MQTT_BROKER, port, keepalive=60)
    client.loop_start()
    logger.info("MQTT client started at %s:%s", MQTT_BROKER, port)


def subscribe(topic: str, callback: Callable):
    """Register a callback for a topic pattern."""
    with _state_lock:
        is_new_topic = topic not in _subscribers
        callbacks = _subscribers.setdefault(topic, [])
        if callback in callbacks:
            return
        callbacks.append(callback)
        client = _client
        if is_new_topic and client and _connected:
            client.subscribe(topic)


def is_mqtt_connected() -> bool:
    with _state_lock:
        client = _client
        connected = _connected
    return bool(client and connected)


def publish_message(topic: str, payload: str, qos: int = 1):
    """Publish a message or raise if MQTT is unavailable."""
    with _state_lock:
        client = _client
        connected = _connected
    if client and connected:
        result = client.publish(topic, payload, qos=qos)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("MQTT publish rejected: %s, rc=%s", topic, result.rc)
            raise RuntimeError(f"mqtt_publish_failed:{result.rc}")
        logger.debug("MQTT published: %s -> %s", topic, payload)
        return

    logger.warning("MQTT not connected, dropping message: %s", topic)
    raise RuntimeError("mqtt_not_connected")


def stop_mqtt():
    """Stop the shared MQTT client."""
    global _client, _connected
    with _state_lock:
        client = _client
        _client = None
        _connected = False
        _subscribers.clear()
    if client:
        try:
            client.loop_stop()
        finally:
            client.disconnect()
