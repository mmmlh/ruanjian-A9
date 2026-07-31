"""
Shared device presentation helpers for API payloads and state attributes.
"""
from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

ONLINE_FRESHNESS_WINDOW = timedelta(minutes=10)
MODE_LABELS = {
    "cool": "制冷",
    "heat": "制热",
    "dehumidify": "除湿",
    "fan_only": "送风",
    "auto": "自动",
}


def parse_updated_at(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_last_seen_at(value: str | None, now: datetime | None = None) -> str | None:
    parsed = parse_updated_at(value)
    if parsed is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def is_device_online(value: str | None, now: datetime | None = None) -> bool:
    seen_at = parse_updated_at(value)
    if seen_at is None:
        return False

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    age = current - seen_at
    return timedelta(0) <= age <= ONLINE_FRESHNESS_WINDOW


def load_device_status(device: Mapping[str, Any]) -> dict[str, Any]:
    raw_status = device.get("status")
    if raw_status is not None:
        if isinstance(raw_status, MappingABC):
            return dict(raw_status)
        return {}
    try:
        parsed = json.loads(device.get("status_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, MappingABC):
        return dict(parsed)
    return {}


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mode_label(value: Any) -> str:
    raw = str(value or "auto")
    return MODE_LABELS.get(raw, raw)


def summarize_device_status(device_type: str, status: Mapping[str, Any]) -> str:
    if device_type in {"light", "smart_plug"}:
        return "已开启" if status.get("power") == "on" else "已关闭"
    if device_type == "ac":
        if status.get("power") == "on":
            return f"{_mode_label(status.get('mode', 'cool'))} {status.get('temp', 26)}°C"
        return "待机中"
    if device_type == "door_lock":
        return "已上锁" if status.get("locked", True) else "已解锁"
    if device_type == "temperature_sensor":
        value = status.get("value")
        if value is None:
            return "暂无读数"
        unit = status.get("unit", "celsius")
        if unit == "celsius":
            return f"{value}°C"
        if unit == "fahrenheit":
            return f"{value}°F"
        return f"{value} {unit}"
    if device_type == "humidity_sensor":
        value = status.get("value")
        return f"{value}%" if value is not None else "暂无读数"
    if device_type == "pir_sensor":
        return "检测到活动" if status.get("presence") else "无人活动"
    if device_type == "curtain":
        position = _safe_int(status.get("position"))
        if position is None:
            return "位置未知"
        if position <= 0:
            return "已关闭"
        if position >= 100:
            return "已全开"
        return f"开启 {position}%"
    if device_type == "humidifier":
        if status.get("power") == "on":
            target_humidity = _safe_int(status.get("target_humidity"))
            return f"目标湿度 {target_humidity}%" if target_humidity is not None else "运行中"
        return "已关闭"
    return json.dumps(status, ensure_ascii=False)


def present_device(
    device: Mapping[str, Any],
    *,
    now: datetime | None = None,
    include_status: bool = False,
) -> dict[str, Any]:
    presented = dict(device)
    status = load_device_status(presented)
    last_seen_source = presented.get("updated_at") or presented.get("created_at")

    recently_seen = is_device_online(last_seen_source, now=now)
    reported_online = status.get("online")
    presented["online"] = recently_seen and reported_online is not False
    presented["status_summary"] = summarize_device_status(str(presented.get("type", "")), status)
    presented["last_seen_at"] = format_last_seen_at(last_seen_source, now=now)

    if include_status:
        presented["status"] = status

    return presented
