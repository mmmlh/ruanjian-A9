"""
MQTT client helpers for backend publish/subscribe.
"""
import json
import logging
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


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected to %s:%s", MQTT_BROKER, MQTT_PORT)
        for topic in _subscribers:
            client.subscribe(topic)
            logger.info("MQTT subscribed: %s", topic)
    else:
        logger.error("MQTT connection failed, rc=%s", rc)


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
        _client.connect(MQTT_BROKER, port, keepalive=60)
        _client.loop_start()
        logger.info("MQTT client started at %s:%s", MQTT_BROKER, port)
    except Exception as exc:
        logger.warning("MQTT connection failed and will need retry later: %s", exc)


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
