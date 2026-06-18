"""
智能门禁控制器模拟器 — 远程开锁/上锁
"""
import json
import time
from base_device import BaseDevice


class DoorLock(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "door_lock", **kwargs)
        self.locked = True

    def generate_data(self) -> dict:
        # 门禁不主动产生数据
        return None

    def handle_command(self, payload: dict):
        action = payload.get("action")

        if action == "unlock":
            auth_code = payload.get("auth_code", "")
            # 简单验证（实际项目中应验证 AES 加密的认证码）
            if auth_code:
                self.locked = False
                success = True
            else:
                success = False
        elif action == "lock":
            self.locked = True
            success = True
        else:
            success = False

        status = {
            "locked": self.locked,
            "device_id": f"door_{self.device_id:03d}",
        }
        self.publish_status(status)
        self._publish_response(success, status)

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
