"""
帘控制器模拟器 — 支持开合度控制 0-100%
"""
import json
import time
from base_device import BaseDevice


class CurtainController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "curtain", **kwargs)
        self.position = 0

    def generate_data(self) -> dict:
        return None

    def handle_command(self, payload: dict):
        action = payload.get("action")
        if action == "open":
            self.position = 100
        elif action == "close":
            self.position = 0
        elif action == "set":
            if "position" in payload:
                self.position = max(0, min(100, payload["position"]))
        status = {
            "position": self.position,
            "device_id": f"curtain_{self.device_id:03d}",
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
