"""
智能门禁控制器模拟器 — 远程开锁/上锁
"""
import time
from base_device import BaseDevice


class DoorLock(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "door_lock", **kwargs)
        self.locked = True

    def generate_data(self) -> dict:
        # 门禁不主动产生数据
        return None

    def capabilities(self) -> dict:
        return {
            "actions": ["unlock", "lock"],
            "params": {"auth_code": {"min_length": 16, "required_for": ["unlock"]}},
        }

    def handle_command(self, payload: dict):
        action = payload.get("action")

        if action == "unlock":
            auth_code = payload.get("auth_code", "")
            if isinstance(auth_code, str) and len(auth_code) >= 16:
                self.locked = False
                success = True
                error_code = None
            else:
                success = False
                error_code = "AUTH_FAILED"
        elif action == "lock":
            self.locked = True
            success = True
            error_code = None
        else:
            success = False
            error_code = "UNSUPPORTED_ACTION"

        state = {"locked": self.locked}
        status = {**state, "device_id": f"door_{self.device_id:03d}"}
        self.publish_status(status, payload.get("command_id"))
        self.publish_ack(payload, success, state, error_code)

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
