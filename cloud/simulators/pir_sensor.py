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

    def generate_data(self) -> dict:
        now = time.time()
        if now - self.last_change > self.change_interval:
            self.presence = not self.presence
            self.last_change = now
            self.change_interval = random.randint(10, 30)
            return {
                "presence": self.presence,
                "device_id": f"pir_{self.device_id:03d}",
                "ts": int(now),
            }
        return None  # 状态未变化时不发布

    def handle_command(self, payload: dict):
        pass

    def _sleep(self):
        """PIR 传感器每秒检查一次"""
        for _ in range(10):
            if not self.running:
                break
            time.sleep(0.1)
