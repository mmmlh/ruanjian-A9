"""
帘控制器模拟器 — 支持开合度控制 0-100%
"""
import time
from base_device import BaseDevice


class CurtainController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "curtain", **kwargs)
        self.position = 0
        self.motion = "stopped"

    def generate_data(self) -> dict:
        return None

    def capabilities(self) -> dict:
        return {"actions": ["open", "close", "set"], "params": {"position": {"min": 0, "max": 100}}}

    def handle_command(self, payload: dict):
        action = payload.get("action")
        if action == "open":
            self.position = 100
            success, error_code = True, None
        elif action == "close":
            self.position = 0
            success, error_code = True, None
        elif action == "set":
            position = payload.get("position")
            if isinstance(position, (int, float)) and 0 <= position <= 100:
                self.position = position
                success, error_code = True, None
            else:
                success, error_code = False, "INVALID_PARAMS"
        else:
            success, error_code = False, "UNSUPPORTED_ACTION"
        self.motion = "stopped"
        state = {"position": self.position, "motion": self.motion}
        status = {**state, "device_id": f"curtain_{self.device_id:03d}"}
        self.publish_status(status, payload.get("command_id"))
        self.publish_ack(payload, success, state, error_code)

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
