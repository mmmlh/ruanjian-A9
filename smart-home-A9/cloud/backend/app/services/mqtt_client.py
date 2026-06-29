"""
MQTT 客户端：连接 Broker、订阅主题、发布消息
"""
import json
import logging
import threading
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.config import MQTT_BROKER, MQTT_PORT, MQTT_USE_TLS, MQTT_TLS_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CA_CERTS

logger = logging.getLogger(__name__)

# 全局 MQTT 客户端实例
_client: Optional[mqtt.Client] = None
_subscribers: dict[str, list[Callable]] = {}


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"MQTT 已连接: {MQTT_BROKER}:{MQTT_PORT}")
        # 重新订阅所有主题
        for topic in _subscribers:
            client.subscribe(topic)
            logger.info(f"MQTT 订阅: {topic}")
    else:
        logger.error(f"MQTT 连接失败, rc={rc}")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        payload = msg.payload.decode("utf-8")

    logger.debug(f"MQTT 收到: {topic} -> {payload}")

    # 通知所有匹配的订阅者
    for pattern, callbacks in _subscribers.items():
        if _topic_match(pattern, topic):
            for cb in callbacks:
                try:
                    cb(topic, payload)
                except Exception as e:
                    logger.error(f"MQTT 回调异常: {e}")


def _topic_match(pattern: str, topic: str) -> bool:
    """简单的 MQTT 主题匹配（支持 # 通配符）"""
    if pattern == "#":
        return True
    if pattern.endswith("/#"):
        prefix = pattern[:-2]
        return topic.startswith(prefix)
    return pattern == topic


def init_mqtt():
    """初始化 MQTT 客户端并连接"""
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
            _client.tls_set()  # 使用系统 CA 证书

    port = MQTT_TLS_PORT if MQTT_USE_TLS else MQTT_PORT
    try:
        _client.connect(MQTT_BROKER, port, keepalive=60)
        _client.loop_start()
        logger.info(f"MQTT 客户端启动: {MQTT_BROKER}:{port}")
    except Exception as e:
        logger.warning(f"MQTT 连接失败（稍后重试）: {e}")


def subscribe(topic: str, callback: Callable):
    """订阅主题并注册回调"""
    if topic not in _subscribers:
        _subscribers[topic] = []
        if _client and _client.is_connected():
            _client.subscribe(topic)
    _subscribers[topic].append(callback)


def publish_message(topic: str, payload: str, qos: int = 1):
    """发布 MQTT 消息"""
    if _client and _client.is_connected():
        _client.publish(topic, payload, qos=qos)
        logger.debug(f"MQTT 发布: {topic} -> {payload}")
    else:
        logger.warning(f"MQTT 未连接，消息丢弃: {topic}")


def stop_mqtt():
    """停止 MQTT 客户端"""
    global _client
    if _client:
        _client.loop_stop()
        _client.disconnect()
        _client = None
