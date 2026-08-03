"""
人体感应传感器模拟器 — 随机切换有人/无人状态
"""
import time
import random
from base_device import BaseDevice


class PIRSensor(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "pir_sensor", **kwargs)
        self.presence = False
        self.last_change = time.time()
        self.change_interval = random.randint(10, 30)  # 10-30秒切换一次
        self.reporting_enabled = True

    def capabilities(self) -> dict:
        return {
            "actions": ["set_config"],
            "params": {
                "detection_interval_seconds": {"min": 1, "max": 300},
                "reporting_enabled": {"values": [True, False]},
            },
        }

    def generate_data(self) -> dict:
        now = time.time()
        if now - self.last_change > self.change_interval:
            self.presence = not self.presence
            self.last_change = now
            if self.reporting_enabled:
                self.change_interval = random.randint(10, 30)
            else:
                return None
            return {
                "presence": self.presence,
                "device_id": f"pir_{self.device_id:03d}",
                "ts": int(now),
            }
        return None  # 状态未变化时不发布

    def handle_command(self, payload: dict):
        interval = payload.get("detection_interval_seconds", self.change_interval)
        reporting_enabled = payload.get("reporting_enabled", self.reporting_enabled)
        if (
            payload.get("action") != "set_config"
            or not isinstance(interval, (int, float)) or not 1 <= interval <= 300
            or not isinstance(reporting_enabled, bool)
        ):
            self.publish_status(
                {**self._config_state(), "device_id": f"pir_{self.device_id:03d}"},
                payload.get("command_id"),
            )
            self.publish_ack(payload, False, self._config_state(), "INVALID_PARAMS")
            return
        self.change_interval = interval
        self.reporting_enabled = reporting_enabled
        self.publish_status(
            {**self._config_state(), "device_id": f"pir_{self.device_id:03d}"},
            payload.get("command_id"),
        )
        self.publish_ack(payload, True, self._config_state())

    def _config_state(self) -> dict:
        return {
            "detection_interval_seconds": self.change_interval,
            "reporting_enabled": self.reporting_enabled,
        }

    def _sleep(self):
        """PIR 传感器每秒检查一次"""
        for _ in range(10):
            if not self.running:
                break
            time.sleep(0.1)
