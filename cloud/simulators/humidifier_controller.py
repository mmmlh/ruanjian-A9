"""
加湿器控制器模拟器 — 支持开关、档位、目标湿度
"""
import json
import time
from base_device import BaseDevice


class HumidifierController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "humidifier", **kwargs)
        self.power = "off"
        self.level = 2
        self.target_humidity = 60

    def generate_data(self) -> dict:
        return None

    def handle_command(self, payload: dict):
        action = payload.get("action")
        if action == "on":
            self.power = "on"
        elif action == "off":
            self.power = "off"
        elif action == "set":
            if "level" in payload:
                self.level = max(1, min(3, payload["level"]))
            if "target_humidity" in payload:
                self.target_humidity = max(30, min(90, payload["target_humidity"]))
            if "power" in payload:
                self.power = payload["power"]
        status = {
            "power": self.power,
            "level": self.level,
            "target_humidity": self.target_humidity,
            "device_id": f"humidifier_{self.device_id:03d}",
        }
        self.publish_status(status)
        self._publish_response(True, status)

    def _publish_response(self, success: bool, state: dict):
        topic = f"{self.topic_base}/response"
        resp = {"success": success, "state": state}
        if self.client:
            self.client.publish(topic, json.dumps(resp), qos=1)

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
