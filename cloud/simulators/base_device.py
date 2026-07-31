"""Shared MQTT lifecycle for simulated devices."""

from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)
HEARTBEAT_INTERVAL_SECONDS = 30


class BaseDevice(ABC):
    """Base class used by every simulated device."""

    def __init__(
        self,
        device_id: int,
        room_id: str,
        device_type: str,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
    ):
        self.device_id = device_id
        self.room_id = room_id
        self.device_type = device_type
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.client: mqtt.Client | None = None
        self.running = False
        self.connected = False
        self.last_error: str | None = None
        self.last_command: dict | None = None
        self.last_status: dict | None = None
        self.last_sensor_data: dict | None = None
        self.last_activity_at: float | None = None
        self._thread: threading.Thread | None = None

        self.topic_base = f"home/{room_id}/{device_type}"
        self.topic_command = f"{self.topic_base}/command"
        self.topic_status = f"{self.topic_base}/status"
        self.topic_sensor = f"{self.topic_base}/sensor"
        self.topic_availability = f"{self.topic_base}/availability"
        self._last_heartbeat_at: float | None = None

    def connect_mqtt(self):
        """Connect to the configured MQTT broker and subscribe for commands."""
        self.client = mqtt.Client(
            client_id=f"sim_{self.device_type}_{self.device_id}",
            protocol=mqtt.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.will_set(
            self.topic_availability,
            json.dumps(self._availability_payload(False)),
            qos=1,
            retain=True,
        )
        self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
        self.client.loop_start()
        logger.info("[%s] MQTT connecting to %s:%s", self, self.mqtt_broker, self.mqtt_port)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.last_error = None
            client.subscribe(self.topic_command)
            self.publish_availability(True)
            logger.info("[%s] subscribed to %s", self, self.topic_command)
        else:
            self.connected = False
            self.last_error = f"MQTT connection failed with code {rc}"

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc:
            self.last_error = f"MQTT disconnected with code {rc}"

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.last_command = payload
            self.last_activity_at = time.time()
            logger.info("[%s] command received: %s", self, payload)
            self.handle_command(payload)
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("[%s] command handling failed", self)

    @abstractmethod
    def handle_command(self, payload: dict):
        """Apply a command payload received from MQTT."""

    @abstractmethod
    def generate_data(self) -> dict | None:
        """Return the next sensor reading, or None when no reading is due."""

    def publish_status(self, status: dict):
        self.last_status = dict(status)
        self.last_activity_at = time.time()
        if self.client:
            self.client.publish(self.topic_status, json.dumps(status), qos=1)

    def publish_sensor_data(self, data: dict):
        self.last_sensor_data = dict(data)
        self.last_activity_at = time.time()
        if self.client:
            self.client.publish(self.topic_sensor, json.dumps(data), qos=1)

    def _availability_payload(self, online: bool) -> dict:
        return {
            "online": online,
            "device_id": f"{self.device_type}_{self.device_id:03d}",
            "ts": int(time.time()),
        }

    def publish_availability(self, online: bool):
        if not self.client:
            return None
        self._last_heartbeat_at = time.time() if online else None
        return self.client.publish(
            self.topic_availability,
            json.dumps(self._availability_payload(online)),
            qos=1,
            retain=True,
        )

    def start(self):
        if self.running:
            return
        self.running = True
        self.last_error = None
        try:
            self.connect_mqtt()
        except Exception as exc:
            self.running = False
            self.connected = False
            self.last_error = str(exc)
            raise
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("[%s] started", self)

    def _run_loop(self):
        while self.running:
            try:
                data = self.generate_data()
                if data:
                    self.publish_sensor_data(data)
                now = time.time()
                if self.connected and (
                    self._last_heartbeat_at is None
                    or now - self._last_heartbeat_at >= HEARTBEAT_INTERVAL_SECONDS
                ):
                    self.publish_availability(True)
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception("[%s] simulation cycle failed", self)
            self._sleep()

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.client:
            if self.connected:
                publication = self.publish_availability(False)
                if publication:
                    try:
                        publication.wait_for_publish(timeout=2)
                    except (RuntimeError, ValueError):
                        pass
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.connected = False
        logger.info("[%s] stopped", self)

    def __str__(self):
        return f"{self.device_type}#{self.device_id}({self.room_id})"
