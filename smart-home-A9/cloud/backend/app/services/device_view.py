"""
Shared device presentation helpers for API payloads and state attributes.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

ONLINE_FRESHNESS_WINDOW = timedelta(minutes=10)


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


def format_last_seen_at(value: str | None, now: datetime | None = None) -> str:
    parsed = parse_updated_at(value)
    current = now or datetime.now(timezone.utc)
    if parsed is None:
        return current.isoformat()
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
    return current - seen_at <= ONLINE_FRESHNESS_WINDOW


def load_device_status(device: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(device.get("status"), dict):
        return dict(device["status"])
    try:
        return json.loads(device.get("status_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def summarize_device_status(device_type: str, status: Mapping[str, Any]) -> str:
    if device_type in {"light", "smart_plug"}:
        return "Power on" if status.get("power") == "on" else "Power off"
    if device_type == "ac":
        if status.get("power") == "on":
            return f"{status.get('mode', 'cool')} {status.get('temp', 26)}C"
        return "Standby"
    if device_type == "door_lock":
        return "Locked" if status.get("locked", True) else "Unlocked"
    if device_type == "temperature_sensor":
        value = status.get("value")
        unit = status.get("unit", "celsius")
        return f"{value} {unit}" if value is not None else "No reading"
    if device_type == "humidity_sensor":
        value = status.get("value")
        return f"{value}%" if value is not None else "No reading"
    if device_type == "pir_sensor":
        return "Motion detected" if status.get("presence") else "No motion"
    if device_type == "curtain":
        return f"Open {int(status.get('position', 0))}%"
    if device_type == "humidifier":
        if status.get("power") == "on":
            return f"Target humidity {int(status.get('target_humidity', 60))}%"
        return "Power off"
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

    presented["online"] = is_device_online(last_seen_source, now=now)
    presented["status_summary"] = summarize_device_status(str(presented.get("type", "")), status)
    presented["last_seen_at"] = format_last_seen_at(last_seen_source, now=now)

    if include_status:
        presented["status"] = status

    return presented
