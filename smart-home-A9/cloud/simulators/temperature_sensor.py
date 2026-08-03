"""
温度传感器模拟器 — 正态分布随机生成温度值
"""
import random
import time
from base_device import BaseDevice


class TemperatureSensor(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "temperature_sensor", **kwargs)
        self.base_temp = 25.0  # 基准温度
        self.std_dev = 0.5     # 标准差
        self.sample_interval_seconds = 5
        self.calibration = 0.0
        self.reporting_enabled = True

    def capabilities(self) -> dict:
        return {
            "actions": ["set_config"],
            "params": {
                "sample_interval_seconds": {"min": 1, "max": 3600},
                "calibration": {"min": -10, "max": 10},
                "reporting_enabled": {"values": [True, False]},
            },
        }

    def generate_data(self) -> dict:
        if not self.reporting_enabled:
            return None
        temp = round(random.gauss(self.base_temp, self.std_dev) + self.calibration, 1)
        temp = max(15.0, min(38.0, temp))  # 限制范围
        return {
            "value": temp,
            "unit": "celsius",
            "device_id": f"temp_{self.device_id:03d}",
            "ts": int(self._now()),
        }

    def handle_command(self, payload: dict):
        interval = payload.get("sample_interval_seconds", self.sample_interval_seconds)
        calibration = payload.get("calibration", self.calibration)
        reporting_enabled = payload.get("reporting_enabled", self.reporting_enabled)
        if (
            payload.get("action") != "set_config"
            or not isinstance(interval, (int, float)) or not 1 <= interval <= 3600
            or not isinstance(calibration, (int, float)) or not -10 <= calibration <= 10
            or not isinstance(reporting_enabled, bool)
        ):
            self.publish_status(
                {**self._config_state(), "device_id": f"temp_{self.device_id:03d}"},
                payload.get("command_id"),
            )
            self.publish_ack(payload, False, self._config_state(), "INVALID_PARAMS")
            return
        self.sample_interval_seconds = interval
        self.calibration = calibration
        self.reporting_enabled = reporting_enabled
        self.publish_status(
            {**self._config_state(), "device_id": f"temp_{self.device_id:03d}"},
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
