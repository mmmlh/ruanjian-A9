"""
温度传感器模拟器 — 正态分布随机生成温度值
"""
import random
from base_device import BaseDevice


class TemperatureSensor(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "temperature_sensor", **kwargs)
        self.base_temp = 25.0  # 基准温度
        self.std_dev = 0.5     # 标准差

    def generate_data(self) -> dict:
        temp = round(random.gauss(self.base_temp, self.std_dev), 1)
        temp = max(15.0, min(38.0, temp))  # 限制范围
        return {
            "value": temp,
            "unit": "celsius",
            "device_id": f"temp_{self.device_id:03d}",
            "ts": int(self._now()),
        }

    def handle_command(self, payload: dict):
        # 温度传感器通常不接收控制指令
        pass

    def _now(self):
        import time
        return time.time()
