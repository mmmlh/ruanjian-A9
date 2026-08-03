"""
智能灯控制器模拟器 — 支持开关、亮度、色温
"""
import time
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

    def capabilities(self) -> dict:
        return {
            "actions": ["on", "off", "set"],
            "params": {
                "brightness": {"min": 0, "max": 100},
                "color": {"values": ["warm", "neutral", "cool"]},
            },
        }

    def _state(self) -> dict:
        return {
            "power": self.power,
            "brightness": self.brightness,
            "color": self.color,
        }

    def handle_command(self, payload: dict):
        action = payload.get("action")
        success = True
        error_code = None
        if action == "on":
            brightness = payload.get("brightness", 80)
            color = payload.get("color", "warm")
            if not isinstance(brightness, (int, float)) or not 0 <= brightness <= 100:
                success, error_code = False, "INVALID_PARAMS"
            elif color not in {"warm", "neutral", "cool"}:
                success, error_code = False, "INVALID_PARAMS"
            else:
                self.power = "on"
                self.brightness = brightness
                self.color = color
                self.on_time = time.time()
        elif action == "off":
            self.power = "off"
            self.brightness = 0
            self.on_time = None
        elif action == "set":
            brightness = payload.get("brightness")
            color = payload.get("color")
            if brightness is not None and (not isinstance(brightness, (int, float)) or not 0 <= brightness <= 100):
                success, error_code = False, "INVALID_PARAMS"
            elif color is not None and color not in {"warm", "neutral", "cool"}:
                success, error_code = False, "INVALID_PARAMS"
            else:
                if brightness is not None:
                    self.brightness = brightness
                if color is not None:
                    self.color = color
        else:
            success, error_code = False, "UNSUPPORTED_ACTION"

        state = self._state()
        status = {**state, "device_id": f"light_{self.device_id:03d}"}
        self.publish_status(status, payload.get("command_id"))
        self.publish_ack(payload, success, state, error_code)

    def get_state(self) -> dict:
        state = {
            "power": self.power,
            "brightness": self.brightness,
            "color": self.color,
        }
        if self.on_time:
            state["on_duration_sec"] = int(time.time() - self.on_time)
        return state

    def _sleep(self):
        """灯控制器空闲等待"""
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
