import json
from typing import Any

from fastapi import HTTPException

from app.database.connection import get_db
from app.services.entity_state import build_state, parse_entity_id
from app.services.mqtt_client import publish_message
from app.services.security import aes_decrypt


SUPPORTED_ACTIONS_BY_DEVICE_TYPE: dict[str, tuple[str, ...]] = {
    "light": ("on", "off", "set"),
    "ac": ("on", "off", "set"),
    "door_lock": ("unlock", "lock"),
    "curtain": ("open", "close", "set"),
    "humidifier": ("on", "off", "set"),
    "smart_plug": ("on", "off", "set"),
}

ACTION_ALIASES_BY_DEVICE_TYPE: dict[str, dict[str, str]] = {
    "light": {"turn_on": "on", "turn_off": "off", "set_brightness": "set"},
    "ac": {"turn_on": "on", "turn_off": "off"},
    "door_lock": {"open": "unlock", "close": "lock"},
    "humidifier": {"turn_on": "on", "turn_off": "off"},
    "smart_plug": {"turn_on": "on", "turn_off": "off"},
}

PARAMETER_RANGES_BY_DEVICE_TYPE: dict[str, dict[str, tuple[float, float]]] = {
    "light": {"brightness": (0, 100)},
    "ac": {"temp": (16, 30)},
    "curtain": {"position": (0, 100)},
    "humidifier": {"level": (1, 3), "target_humidity": (30, 80)},
}


def normalize_and_validate_command(
    device_type: str,
    action: str,
    params: Any,
) -> tuple[str, dict[str, Any]]:
    if not isinstance(action, str):
        raise HTTPException(status_code=400, detail="unsupported_device_action")

    requested_action = action.strip().lower()
    canonical_action = ACTION_ALIASES_BY_DEVICE_TYPE.get(device_type, {}).get(
        requested_action,
        requested_action,
    )
    if canonical_action not in SUPPORTED_ACTIONS_BY_DEVICE_TYPE.get(device_type, ()):
        raise HTTPException(status_code=400, detail="unsupported_device_action")
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="invalid_command_params")

    normalized_params = dict(params)
    if device_type == "door_lock" and canonical_action == "unlock":
        auth_code = normalized_params.get("auth_code")
        if not isinstance(auth_code, str) or not auth_code.strip():
            raise HTTPException(status_code=400, detail="invalid_command_params")

    if canonical_action in {"on", "off"} and "power" in normalized_params:
        power = normalized_params["power"]
        if not isinstance(power, str) or power != canonical_action:
            raise HTTPException(status_code=400, detail="invalid_command_params")

    for name, (minimum, maximum) in PARAMETER_RANGES_BY_DEVICE_TYPE.get(device_type, {}).items():
        if name not in normalized_params:
            continue
        value = normalized_params[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail="invalid_command_params")
        if not minimum <= value <= maximum:
            raise HTTPException(status_code=400, detail="invalid_command_params")

    try:
        json.dumps(normalized_params, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid_command_params") from exc

    return canonical_action, normalized_params


def decode_command_payload(action: str, params: Any, user: dict) -> tuple[str, Any]:
    if isinstance(params, dict) and "encrypted" in params:
        aes_key = user.get("aes_key", "")
        if not aes_key:
            raise HTTPException(status_code=400, detail="密钥未配置")
        try:
            decrypted = aes_decrypt(params["encrypted"], aes_key)
            decrypted_cmd = json.loads(decrypted)
        except Exception as exc:  # pragma: no cover - exact crypto failures are covered elsewhere
            raise HTTPException(status_code=400, detail=f"解密失败: {str(exc)}") from exc

        if not isinstance(decrypted_cmd, dict):
            raise HTTPException(status_code=400, detail="invalid_command_params")

        actual_action = decrypted_cmd.get("action", action)
        actual_params = decrypted_cmd.get("params", {})
        return actual_action, actual_params

    return action, {} if params is None else params


def apply_command_to_status(device_type: str, current_status: dict[str, Any], action: str, params: dict[str, Any]) -> dict[str, Any]:
    status = dict(current_status)
    normalized_action = action.lower()

    if device_type == "light":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
            status["brightness"] = 0
        elif "power" in params:
            status["power"] = params["power"]
        if normalized_action not in {"off", "turn_off"} and "brightness" in params:
            status["brightness"] = params["brightness"]
        if "color" in params:
            status["color"] = params["color"]

    elif device_type == "ac":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        elif "power" in params:
            status["power"] = params["power"]
        for key in ("mode", "temp", "fan"):
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
            status["position"] = params["position"]

    elif device_type == "humidifier":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        elif "power" in params:
            status["power"] = params["power"]
        for key in ("level", "target_humidity"):
            if key in params:
                status[key] = params[key]

    elif device_type == "smart_plug":
        if normalized_action in {"on", "turn_on"}:
            status["power"] = "on"
        elif normalized_action in {"off", "turn_off"}:
            status["power"] = "off"
        elif "power" in params:
            status["power"] = params["power"]
        for key in ("power_watts", "total_kwh"):
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

        decoded_action, decoded_params = decode_command_payload(action, params, user)
        actual_action, actual_params = normalize_and_validate_command(
            device["type"],
            decoded_action,
            decoded_params,
        )
        payload = {**actual_params, "action": actual_action}
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
