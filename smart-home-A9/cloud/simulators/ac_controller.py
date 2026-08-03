"""
空调控制器模拟器 — 支持多品牌（海尔/格力/美的）
"""
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

    def capabilities(self) -> dict:
        return {
            "actions": ["on", "off", "set"],
            "params": {
                "power": {"values": ["on", "off"]},
                "mode": {"values": ["cool", "heat", "dehumidify", "fan_only", "auto"]},
                "temp": {"min": 16, "max": 30},
                "fan": {"values": ["auto", "low", "medium", "high"]},
                "swing": {"values": ["on", "off"]},
            },
        }

    def _state(self) -> dict:
        return {"power": self.power, "mode": self.mode, "temp": self.temp, "fan": self.fan, "swing": self.swing}

    def handle_command(self, payload: dict):
        action = payload.get("action")
        values = self.capabilities()["params"]
        updates = {key: payload[key] for key in ("power", "mode", "temp", "fan", "swing") if key in payload}
        invalid = (
            action not in {"on", "off", "set"}
            or ("power" in updates and updates["power"] not in values["power"]["values"])
            or ("mode" in updates and updates["mode"] not in values["mode"]["values"])
            or ("fan" in updates and updates["fan"] not in values["fan"]["values"])
            or ("swing" in updates and updates["swing"] not in values["swing"]["values"])
            or ("temp" in updates and (not isinstance(updates["temp"], (int, float)) or not 16 <= updates["temp"] <= 30))
        )
        if invalid:
            success, error_code = False, "INVALID_PARAMS" if action in {"on", "off", "set"} else "UNSUPPORTED_ACTION"
        elif action == "off":
            self.power = "off"
            success, error_code = True, None
        else:
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
            success, error_code = True, None

        brand_cmd = self._translate_to_brand()
        state = self._state()
        status = {**state, "brand": self.brand, "brand_command": brand_cmd, "device_id": f"ac_{self.device_id:03d}"}
        self.publish_status(status, payload.get("command_id"))
        self.publish_ack(payload, success, state, error_code)

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

    def _sleep(self):
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)
