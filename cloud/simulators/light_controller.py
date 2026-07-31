"""
智能灯控制器模拟器 — 支持开关、亮度、色温
"""
import time
import json
from base_device import BaseDevice


class LightController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "light", **kwargs)
        self.power = "off"
        self.brightness = 0
        self.color = "warm"
        self.on_time = None  # 开灯时间（用于联动规则判断持续时长）

    def generate_data(self) -> dict:
        # 灯不主动产生数据，只在状态变化时上报
        return None

    def handle_command(self, payload: dict):
        action = payload.get("action")
        if action == "on":
            self.power = "on"
            self.brightness = payload.get("brightness", 80)
            self.color = payload.get("color", "warm")
            self.on_time = time.time()
        elif action == "off":
            self.power = "off"
            self.brightness = 0
            self.on_time = None
        elif action == "set":
            if "brightness" in payload:
                self.brightness = payload["brightness"]
            if "color" in payload:
                self.color = payload["color"]

        status = {
            "power": self.power,
            "brightness": self.brightness,
            "color": self.color,
            "device_id": f"light_{self.device_id:03d}",
        }
        self.publish_status(status)

        # 响应
        self._publish_response(True, status)

    def get_state(self) -> dict:
        state = {
            "power": self.power,
            "brightness": self.brightness,
            "color": self.color,
        }
        if self.on_time:
            state["on_duration_sec"] = int(time.time() - self.on_time)
        return state

    def _publish_response(self, success: bool, state: dict):
        topic = f"{self.topic_base}/response"
        resp = {"success": success, "state": state}
        if self.client:
            self.client.publish(topic, json.dumps(resp), qos=1)

    def _sleep(self):
        """灯控制器空闲等待"""
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
