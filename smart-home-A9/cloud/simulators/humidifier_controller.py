"""
加湿器控制器模拟器 — 支持开关、档位、目标湿度
"""
import time
from base_device import BaseDevice


class HumidifierController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "humidifier", **kwargs)
        self.power = "off"
        self.level = 2
        self.target_humidity = 60
        self.water_level = 100

    def generate_data(self) -> dict:
        return None

    def capabilities(self) -> dict:
        return {
            "actions": ["on", "off", "set"],
            "params": {
                "power": {"values": ["on", "off"]},
                "level": {"min": 1, "max": 3},
                "target_humidity": {"min": 30, "max": 80},
            },
        }

    def handle_command(self, payload: dict):
        action = payload.get("action")
        if action == "on":
            if self.water_level <= 0:
                success, error_code = False, "WATER_EMPTY"
            else:
                self.power = "on"
                success, error_code = True, None
        elif action == "off":
            self.power = "off"
            success, error_code = True, None
        elif action == "set":
            level = payload.get("level", self.level)
            target = payload.get("target_humidity", self.target_humidity)
            power = payload.get("power", self.power)
            if (
                not isinstance(level, (int, float)) or not 1 <= level <= 3
                or not isinstance(target, (int, float)) or not 30 <= target <= 80
                or power not in {"on", "off"}
            ):
                success, error_code = False, "INVALID_PARAMS"
            elif power == "on" and self.water_level <= 0:
                success, error_code = False, "WATER_EMPTY"
            else:
                self.level = level
                self.target_humidity = target
                self.power = power
                success, error_code = True, None
        else:
            success, error_code = False, "UNSUPPORTED_ACTION"
        state = {"power": self.power, "level": self.level, "target_humidity": self.target_humidity, "water_level": self.water_level}
        status = {**state, "device_id": f"humidifier_{self.device_id:03d}"}
        self.publish_status(status, payload.get("command_id"))
        self.publish_ack(payload, success, state, error_code)

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
