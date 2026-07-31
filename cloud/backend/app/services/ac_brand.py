"""
多品牌空调指令翻译器
统一指令模型 -> 品牌专属协议
"""

# 统一指令模型字段
# power:   "on" | "off"
# mode:    "cool" | "heat" | "dehumidify" | "fan_only" | "auto"
# temp:    16-30
# fan:     "auto" | "low" | "medium" | "high"
# swing:   "on" | "off"

UNIVERSAL_TO_BRAND = {
    "gree": {
        "power": {"on": "PWR_ON", "off": "PWR_OFF"},
        "mode": {
            "cool": "MODE_COOL", "heat": "MODE_HEAT",
            "dehumidify": "MODE_DRY", "fan_only": "MODE_FAN",
            "auto": "MODE_AUTO",
        },
        "fan": {
            "auto": "FAN_AUTO", "low": "FAN_1",
            "medium": "FAN_2", "high": "FAN_3",
        },
        "temp": lambda t: f"TEMP_{t}",
        "swing": {"on": "SWING_ON", "off": "SWING_OFF"},
    },
    "haier": {
        "power": {"on": "POWER=1", "off": "POWER=0"},
        "mode": {
            "cool": "MODE=COOLING", "heat": "MODE=HEATING",
            "dehumidify": "MODE=DRY", "fan_only": "MODE=FAN",
            "auto": "MODE=SMART",
        },
        "fan": {
            "auto": "FAN=AUTO", "low": "FAN=LOW",
            "medium": "FAN=MED", "high": "FAN=HIGH",
        },
        "temp": lambda t: f"SET_TEMP={t}",
        "swing": {"on": "SWING=1", "off": "SWING=0"},
    },
    "midea": {
        "power": {"on": 1, "off": 0},
        "mode": {
            "cool": 2, "heat": 3, "dehumidify": 4,
            "fan_only": 1, "auto": 0,
        },
        "fan": {"auto": 1024, "low": 40, "medium": 60, "high": 80},
        "temp": lambda t: t,
        "swing": {"on": 1, "off": 0},
    },
}


def translate_command(universal_cmd: dict, brand: str) -> dict:
    """
    将统一指令翻译为品牌专属指令

    Args:
        universal_cmd: {"power": "on", "mode": "cool", "temp": 24, "fan": "auto"}
        brand: "gree" | "haier" | "midea" | "generic"

    Returns:
        品牌专属指令字典
    """
    if brand not in UNIVERSAL_TO_BRAND:
        # generic 品牌直接返回统一指令
        return universal_cmd

    brand_map = UNIVERSAL_TO_BRAND[brand]
    result = {}

    for key, value in universal_cmd.items():
        if key in brand_map:
            mapper = brand_map[key]
            if callable(mapper):
                result[key] = mapper(value)
            elif isinstance(mapper, dict):
                result[key] = mapper.get(value, value)
            else:
                result[key] = value
        else:
            result[key] = value

    result["_brand"] = brand
    return result


def get_supported_brands() -> list[str]:
    """获取支持的空调品牌列表"""
    return list(UNIVERSAL_TO_BRAND.keys()) + ["generic"]
