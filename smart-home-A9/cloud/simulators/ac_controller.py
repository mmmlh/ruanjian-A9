"""
空调控制器模拟器 — 支持多品牌（海尔/格力/美的）
"""
import json
import time
from base_device import BaseDevice

# 品牌翻译表（与后端 ac_brand.py 一致）
BRAND_MAP = {
    "gree": {
        "power": {"on": "PWR_ON", "off": "PWR_OFF"},
        "mode": {"cool": "MODE_COOL", "heat": "MODE_HEAT",
                 "dehumidify": "MODE_DRY", "fan_only": "MODE_FAN", "auto": "MODE_AUTO"},
        "fan": {"auto": "FAN_AUTO", "low": "FAN_1", "medium": "FAN_2", "high": "FAN_3"},
        "temp": lambda t: f"TEMP_{t}",
    },
    "haier": {
        "power": {"on": "POWER=1", "off": "POWER=0"},
        "mode": {"cool": "MODE=COOLING", "heat": "MODE=HEATING",
                 "dehumidify": "MODE=DRY", "fan_only": "MODE=FAN", "auto": "MODE=SMART"},
        "fan": {"auto": "FAN=AUTO", "low": "FAN=LOW", "medium": "FAN=MED", "high": "FAN=HIGH"},
        "temp": lambda t: f"SET_TEMP={t}",
    },
    "midea": {
        "power": {"on": 1, "off": 0},
        "mode": {"cool": 2, "heat": 3, "dehumidify": 4, "fan_only": 1, "auto": 0},
        "fan": {"auto": 1024, "low": 40, "medium": 60, "high": 80},
        "temp": lambda t: t,
    },
}


class ACController(BaseDevice):

    def __init__(self, device_id: int, room_id: str, brand: str = "generic", **kwargs):
        super().__init__(device_id, room_id, "ac", **kwargs)
        self.brand = brand
        self.power = "off"
        self.mode = "cool"
        self.temp = 26
        self.fan = "auto"
        self.swing = "off"

    def generate_data(self) -> dict:
        # 空调不主动产生数据
        return None

    def handle_command(self, payload: dict):
        action = payload.get("action")

        if action == "off":
            self.power = "off"
        elif action in ("on", "set"):
            if "power" in payload:
                self.power = payload["power"]
            elif action == "on":
                self.power = "on"
            if "mode" in payload:
                self.mode = payload["mode"]
            if "temp" in payload:
                self.temp = payload["temp"]
            if "fan" in payload:
                self.fan = payload["fan"]
            if "swing" in payload:
                self.swing = payload["swing"]

        # 翻译为品牌指令（用于日志/演示）
        brand_cmd = self._translate_to_brand()

        status = {
            "power": self.power,
            "mode": self.mode,
            "temp": self.temp,
            "fan": self.fan,
            "swing": self.swing,
            "brand": self.brand,
            "brand_command": brand_cmd,
            "device_id": f"ac_{self.device_id:03d}",
        }
        self.publish_status(status)
        self._publish_response(True, status)

    def _translate_to_brand(self) -> dict:
        """将当前状态翻译为品牌专属指令"""
        if self.brand not in BRAND_MAP:
            return {"raw": "generic"}
        bm = BRAND_MAP[self.brand]
        result = {}
        result["power"] = bm["power"].get(self.power, self.power)
        result["mode"] = bm["mode"].get(self.mode, self.mode)
        result["fan"] = bm["fan"].get(self.fan, self.fan)
        result["temp"] = bm["temp"](self.temp) if callable(bm["temp"]) else self.temp
        return result

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
