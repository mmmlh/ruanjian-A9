"""
湿度传感器模拟器
"""
import random
from base_device import BaseDevice


class HumiditySensor(BaseDevice):

    def __init__(self, device_id: int, room_id: str, **kwargs):
        super().__init__(device_id, room_id, "humidity_sensor", **kwargs)
        self.base_humidity = 55.0
        self.std_dev = 5.0

    def generate_data(self) -> dict:
        humidity = round(random.gauss(self.base_humidity, self.std_dev), 1)
        humidity = max(20.0, min(95.0, humidity))
        return {
            "value": humidity,
            "unit": "percent",
            "device_id": f"hum_{self.device_id:03d}",
            "ts": int(self._now()),
        }

    def handle_command(self, payload: dict):
        pass

    def _now(self):
        import time
        return time.time()
