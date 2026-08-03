"""
湿度传感器模拟器
"""
import random
import time
from base_device import BaseDevice


class HumiditySensor(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "humidity_sensor", **kwargs)
        self.base_humidity = 55.0
        self.std_dev = 5.0
        self.sample_interval_seconds = 5
        self.calibration = 0.0
        self.reporting_enabled = True

    def capabilities(self) -> dict:
        return {
            "actions": ["set_config"],
            "params": {
                "sample_interval_seconds": {"min": 1, "max": 3600},
                "calibration": {"min": -20, "max": 20},
                "reporting_enabled": {"values": [True, False]},
            },
        }

    def generate_data(self) -> dict:
        if not self.reporting_enabled:
            return None
        humidity = round(random.gauss(self.base_humidity, self.std_dev) + self.calibration, 1)
        humidity = max(20.0, min(95.0, humidity))
        return {
            "value": humidity,
            "unit": "percent",
            "device_id": f"hum_{self.device_id:03d}",
            "ts": int(self._now()),
        }

    def handle_command(self, payload: dict):
        interval = payload.get("sample_interval_seconds", self.sample_interval_seconds)
        calibration = payload.get("calibration", self.calibration)
        reporting_enabled = payload.get("reporting_enabled", self.reporting_enabled)
        if (
            payload.get("action") != "set_config"
            or not isinstance(interval, (int, float)) or not 1 <= interval <= 3600
            or not isinstance(calibration, (int, float)) or not -20 <= calibration <= 20
            or not isinstance(reporting_enabled, bool)
        ):
            self.publish_status(
                {**self._config_state(), "device_id": f"hum_{self.device_id:03d}"},
                payload.get("command_id"),
            )
            self.publish_ack(payload, False, self._config_state(), "INVALID_PARAMS")
            return
        self.sample_interval_seconds = interval
        self.calibration = calibration
        self.reporting_enabled = reporting_enabled
        self.publish_status(
            {**self._config_state(), "device_id": f"hum_{self.device_id:03d}"},
            payload.get("command_id"),
        )
        self.publish_ack(payload, True, self._config_state())

    def _config_state(self) -> dict:
        return {
            "sample_interval_seconds": self.sample_interval_seconds,
            "calibration": self.calibration,
            "reporting_enabled": self.reporting_enabled,
        }

    def _sleep(self):
        for _ in range(max(1, int(self.sample_interval_seconds * 10))):
            if not self.running:
                break
            time.sleep(0.1)

    def _now(self):
        return time.time()
