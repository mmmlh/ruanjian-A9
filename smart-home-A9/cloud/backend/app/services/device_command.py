import json
from typing import Any

from fastapi import HTTPException

from app.database.connection import get_db
from app.services.entity_state import build_state, parse_entity_id
from app.services.mqtt_client import publish_message
from app.services.device_view import is_device_online
from app.services.security import aes_decrypt


SUPPORTED_ACTIONS_BY_DEVICE_TYPE: dict[str, tuple[str, ...]] = {
    "light": ("on", "off", "set"),
    "ac": ("on", "off", "set"),
    "door_lock": ("unlock", "lock"),
    "curtain": ("open", "close", "set"),
    "humidifier": ("on", "off", "set"),
    "smart_plug": ("on", "off", "set"),
}


def decode_command_payload(action: str, params: dict[str, Any] | None, user: dict) -> tuple[str, dict[str, Any]]:
    if params and "encrypted" in params:
        aes_key = user.get("aes_key", "")
        if not aes_key:
            raise HTTPException(status_code=400, detail="密钥未配置")
        try:
            decrypted = aes_decrypt(params["encrypted"], aes_key)
            decrypted_cmd = json.loads(decrypted)
        except Exception as exc:  # pragma: no cover - exact crypto failures are covered elsewhere
            raise HTTPException(status_code=400, detail=f"解密失败: {str(exc)}") from exc

        actual_action = decrypted_cmd.get("action", action)
        actual_params = decrypted_cmd.get("params", {})
        return actual_action, dict(actual_params)

    return action, dict(params or {})


def apply_command_to_status(device_type: str, current_status: dict[str, Any], action: str, params: dict[str, Any]) -> dict[str, Any]:
    status = dict(current_status)
    normalized_action = action.lower()

    if device_type == "light":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        if "power" in params:
            status["power"] = params["power"]
        if "brightness" in params:
            status["brightness"] = params["brightness"]
        if "color" in params:
            status["color"] = params["color"]

    elif device_type == "ac":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        for key in ("power", "mode", "temp", "fan"):
            if key in params:
                status[key] = params[key]

    elif device_type == "door_lock":
        if normalized_action in {"unlock", "open"}:
            status["locked"] = False
        elif normalized_action in {"lock", "close"}:
            status["locked"] = True
        elif "locked" in params:
            status["locked"] = bool(params["locked"])

    elif device_type == "curtain":
        if normalized_action == "open":
            status["position"] = 100
        elif normalized_action == "close":
            status["position"] = 0
        elif "position" in params:
            status["position"] = int(params["position"])

    elif device_type == "humidifier":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        for key in ("power", "level", "target_humidity"):
            if key in params:
                status[key] = params[key]

    elif device_type == "smart_plug":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        for key in ("power", "power_watts", "total_kwh"):
            if key in params:
                status[key] = params[key]

    elif device_type in {"temperature_sensor", "humidity_sensor"} and "value" in params:
        status["value"] = params["value"]
    elif device_type == "pir_sensor" and "presence" in params:
        status["presence"] = bool(params["presence"])

    return status


def execute_device_command(
    device_id: int,
    action: str,
    params: dict[str, Any] | None,
    user: dict,
    expected_device_type: str | None = None,
) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")

        device = dict(row)
        if expected_device_type and device["type"] != expected_device_type:
            raise HTTPException(status_code=404, detail="entity_id_not_found")

        last_seen_source = device.get("updated_at") or device.get("created_at")
        if not is_device_online(last_seen_source):
            raise HTTPException(status_code=409, detail="device_offline")

        actual_action, actual_params = decode_command_payload(action, params, user)
        payload = {"action": actual_action, **actual_params}
        current_status = json.loads(device.get("status_json") or "{}")
        next_status = apply_command_to_status(device["type"], current_status, actual_action, actual_params)

    topic = device["mqtt_topic"] + "/command"
    try:
        publish_message(topic, json.dumps(payload))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="command_dispatch_failed") from exc

    with get_db() as conn:
        conn.execute(
            "INSERT INTO device_log (device_id, action, detail, user_id) VALUES (?, ?, ?, ?)",
            (device_id, actual_action, json.dumps(payload), int(user["sub"])),
        )
        conn.execute(
            "UPDATE devices SET status_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(next_status), device_id),
        )
        updated = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,),
        ).fetchone()

    return {
        "device_id": device_id,
        "entity_id": f"{device['type']}.device_{device_id}",
        "action": actual_action,
        "payload": payload,
        "topic": topic,
        "changed_state": build_state(dict(updated)) if updated else None,
        "message": f"已下发“{actual_action}”指令",
    }


def execute_entity_command(entity_id: str, action: str, params: dict[str, Any] | None, user: dict) -> dict[str, Any]:
    parsed = parse_entity_id(entity_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="无效的 entity_id 格式")
    return execute_device_command(parsed[1], action, params, user, expected_device_type=parsed[0])
