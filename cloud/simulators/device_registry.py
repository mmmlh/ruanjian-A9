"""Thread-safe runtime registry for the simulator dashboard."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from ac_controller import ACController
from curtain_controller import CurtainController
from door_lock import DoorLock
from humidifier_controller import HumidifierController
from humidity_sensor import HumiditySensor
from light_controller import LightController
from pir_sensor import PIRSensor
from temperature_sensor import TemperatureSensor


DEVICE_CLASSES = {
    "temperature_sensor": TemperatureSensor,
    "humidity_sensor": HumiditySensor,
    "pir_sensor": PIRSensor,
    "light": LightController,
    "ac": ACController,
    "door_lock": DoorLock,
    "curtain": CurtainController,
    "humidifier": HumidifierController,
}

DEVICE_META = {
    "temperature_sensor": {"label": "Temperature", "category": "sensor"},
    "humidity_sensor": {"label": "Humidity", "category": "sensor"},
    "pir_sensor": {"label": "Presence", "category": "sensor"},
    "light": {"label": "Light", "category": "controller"},
    "ac": {"label": "Air conditioner", "category": "controller"},
    "door_lock": {"label": "Door lock", "category": "controller"},
    "curtain": {"label": "Curtain", "category": "controller"},
    "humidifier": {"label": "Humidifier", "category": "controller"},
}

DEFAULT_DEVICE_SPECS = [
    {"id": 1, "room": "livingroom", "type": "temperature_sensor"},
    {"id": 2, "room": "livingroom", "type": "humidity_sensor"},
    {"id": 3, "room": "livingroom", "type": "pir_sensor"},
    {"id": 4, "room": "livingroom", "type": "light"},
    {"id": 5, "room": "livingroom", "type": "ac", "brand": "gree"},
    {"id": 6, "room": "livingroom", "type": "door_lock"},
    {"id": 7, "room": "bedroom", "type": "temperature_sensor"},
    {"id": 8, "room": "bedroom", "type": "humidity_sensor"},
    {"id": 9, "room": "bedroom", "type": "pir_sensor"},
    {"id": 10, "room": "bedroom", "type": "light"},
    {"id": 11, "room": "bedroom", "type": "ac", "brand": "haier"},
    {"id": 12, "room": "study", "type": "temperature_sensor"},
    {"id": 13, "room": "study", "type": "light"},
    {"id": 14, "room": "study", "type": "ac", "brand": "midea"},
    {"id": 15, "room": "livingroom", "type": "curtain"},
    {"id": 16, "room": "study", "type": "curtain"},
    {"id": 17, "room": "bedroom", "type": "humidifier"},
]

ROOM_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class RegistryError(ValueError):
    pass


class DeviceRegistry:
    def __init__(self, mqtt_broker: str, mqtt_port: int, config_path: str | Path):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.config_path = Path(config_path)
        self._lock = threading.RLock()
        self._devices: dict[int, Any] = {}
        self._specs: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self):
        specs = DEFAULT_DEVICE_SPECS
        if self.config_path.exists():
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    specs = raw
            except (OSError, json.JSONDecodeError):
                specs = DEFAULT_DEVICE_SPECS

        for raw_spec in specs:
            spec = self._normalize_spec(raw_spec, require_id=True)
            self._assert_available(spec)
            device = self._create_device(spec)
            self._specs[spec["id"]] = spec
            self._devices[spec["id"]] = device
        self._persist()

    def _normalize_spec(self, raw: dict[str, Any], require_id: bool = False) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise RegistryError("Device configuration must be an object")
        device_type = str(raw.get("type", "")).strip()
        room = str(raw.get("room", "")).strip().lower()
        if device_type not in DEVICE_CLASSES:
            raise RegistryError("Unsupported device type")
        if not ROOM_PATTERN.fullmatch(room):
            raise RegistryError("Room ID must use lowercase letters, numbers, hyphens, or underscores")

        raw_id = raw.get("id")
        if require_id or raw_id is not None:
            try:
                device_id = int(raw_id)
            except (TypeError, ValueError) as exc:
                raise RegistryError("Device ID must be an integer") from exc
            if device_id <= 0:
                raise RegistryError("Device ID must be positive")
        else:
            device_id = self._next_id()

        spec: dict[str, Any] = {
            "id": device_id,
            "room": room,
            "type": device_type,
            "enabled": bool(raw.get("enabled", True)),
        }
        if device_type == "ac":
            brand = str(raw.get("brand", "generic")).strip().lower()
            if brand not in {"gree", "haier", "midea", "generic"}:
                raise RegistryError("Unsupported air-conditioner brand")
            spec["brand"] = brand
        return spec

    def _next_id(self) -> int:
        return max(self._specs, default=0) + 1

    def _assert_available(self, spec: dict[str, Any]):
        if spec["id"] in self._specs:
            raise RegistryError("Device ID already exists")
        for current in self._specs.values():
            if current["room"] == spec["room"] and current["type"] == spec["type"]:
                raise RegistryError("This room already has a simulator of that type")

    def _create_device(self, spec: dict[str, Any]):
        device_class = DEVICE_CLASSES[spec["type"]]
        kwargs: dict[str, Any] = {
            "mqtt_broker": self.mqtt_broker,
            "mqtt_port": self.mqtt_port,
        }
        if spec["type"] == "ac":
            kwargs["brand"] = spec.get("brand", "generic")
        return device_class(spec["id"], spec["room"], **kwargs)

    def _persist(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        payload = [self._specs[key] for key in sorted(self._specs)]
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.config_path)

    def start_all(self):
        with self._lock:
            devices = [
                device
                for device_id, device in self._devices.items()
                if self._specs[device_id].get("enabled", True)
            ]
        for device in devices:
            try:
                device.start()
            except Exception:
                # The dashboard stays available and exposes the connection error.
                continue

    def stop_all(self):
        with self._lock:
            for device in self._devices.values():
                device.stop()

    def list_devices(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._serialize(device_id) for device_id in sorted(self._devices)]

    def get_device(self, device_id: int) -> dict[str, Any]:
        with self._lock:
            self._require_device(device_id)
            return self._serialize(device_id)

    def add_device(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            spec = self._normalize_spec(raw_spec)
            self._assert_available(spec)
            device = self._create_device(spec)
            self._specs[spec["id"]] = spec
            self._devices[spec["id"]] = device
            self._persist()
        if spec["enabled"]:
            try:
                device.start()
            except Exception:
                pass
        with self._lock:
            return self._serialize(spec["id"])

    def remove_device(self, device_id: int):
        with self._lock:
            device = self._require_device(device_id)
            device.stop()
            del self._devices[device_id]
            del self._specs[device_id]
            self._persist()

    def set_running(self, device_id: int, running: bool) -> dict[str, Any]:
        with self._lock:
            device = self._require_device(device_id)
            self._specs[device_id]["enabled"] = running
            self._persist()
        if running:
            try:
                device.start()
            except Exception:
                pass
        else:
            device.stop()
        with self._lock:
            return self._serialize(device_id)

    def send_command(self, device_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            device = self._require_device(device_id)
            if DEVICE_META[device.device_type]["category"] != "controller":
                raise RegistryError("Sensor values must use the sensor endpoint")
            if not isinstance(payload, dict) or not payload.get("action"):
                raise RegistryError("A command action is required")
            if not device.running or not device.client:
                raise RegistryError("Device simulator is stopped")
            result = device.client.publish(device.topic_command, json.dumps(payload), qos=1)
            if getattr(result, "rc", 0) != 0:
                raise RegistryError("MQTT command could not be queued")
            return {"accepted": True, "topic": device.topic_command, "payload": payload}

    def inject_sensor(self, device_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            device = self._require_device(device_id)
            if not device.running:
                raise RegistryError("Device simulator is stopped")
            now = int(time.time())
            if device.device_type == "temperature_sensor":
                value = self._bounded_number(payload.get("value"), 15, 38)
                device.base_temp = value
                reading = {"value": value, "unit": "celsius", "device_id": f"temp_{device_id:03d}", "ts": now}
            elif device.device_type == "humidity_sensor":
                value = self._bounded_number(payload.get("value"), 20, 95)
                device.base_humidity = value
                reading = {"value": value, "unit": "percent", "device_id": f"hum_{device_id:03d}", "ts": now}
            elif device.device_type == "pir_sensor":
                presence = bool(payload.get("presence"))
                device.presence = presence
                device.last_change = time.time()
                reading = {"presence": presence, "device_id": f"pir_{device_id:03d}", "ts": now}
            else:
                raise RegistryError("This device is not a sensor")
            device.publish_sensor_data(reading)
            return {"accepted": True, "topic": device.topic_sensor, "payload": reading}

    @staticmethod
    def _bounded_number(value: Any, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise RegistryError("A numeric sensor value is required") from exc
        return round(max(minimum, min(maximum, number)), 1)

    def _require_device(self, device_id: int):
        device = self._devices.get(device_id)
        if device is None:
            raise RegistryError("Device simulator not found")
        return device

    def _serialize(self, device_id: int) -> dict[str, Any]:
        device = self._devices[device_id]
        spec = dict(self._specs[device_id])
        state = self._read_state(device)
        return {
            **spec,
            "running": device.running,
            "connected": device.connected,
            "topic": device.topic_base,
            "state": state,
            "last_command": device.last_command,
            "last_activity_at": device.last_activity_at,
            "error": device.last_error,
        }

    @staticmethod
    def _read_state(device) -> dict[str, Any]:
        if device.last_status:
            return {
                key: value
                for key, value in device.last_status.items()
                if key not in {"device_id", "brand_command"}
            }
        if device.last_sensor_data:
            return {
                key: value
                for key, value in device.last_sensor_data.items()
                if key not in {"device_id", "ts"}
            }
        fields_by_type = {
            "temperature_sensor": ("base_temp",),
            "humidity_sensor": ("base_humidity",),
            "pir_sensor": ("presence",),
            "light": ("power", "brightness", "color"),
            "ac": ("power", "mode", "temp", "fan", "swing", "brand"),
            "door_lock": ("locked",),
            "curtain": ("position",),
            "humidifier": ("power", "level", "target_humidity"),
        }
        state = {name: getattr(device, name) for name in fields_by_type[device.device_type]}
        if "base_temp" in state:
            state = {"value": state["base_temp"], "unit": "celsius"}
        elif "base_humidity" in state:
            state = {"value": state["base_humidity"], "unit": "percent"}
        return state
