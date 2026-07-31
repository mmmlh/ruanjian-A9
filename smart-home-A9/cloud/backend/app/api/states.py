"""
Home Assistant style device state API: /api/states
"""
import json
import math
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.services.device_command import (
    PARAMETER_RANGES_BY_DEVICE_TYPE,
    execute_entity_command,
)
from app.services.device_state_projection import refresh_device_state
from app.services.entity_state import META_ATTRIBUTE_KEYS, build_state, parse_entity_id

router = APIRouter(prefix="/api/states", tags=["设备状态"])


class ServiceCallRequest(BaseModel):
    entity_id: str
    action: str
    params: Optional[dict[str, Any]] = None


class StateUpdateRequest(BaseModel):
    state: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _validate_state_attributes(device_type: str, attributes: dict[str, Any]) -> None:
    for name, (minimum, maximum) in PARAMETER_RANGES_BY_DEVICE_TYPE.get(
        device_type,
        {},
    ).items():
        if name not in attributes:
            continue
        value = attributes[name]
        if not _is_finite_number(value) or not minimum <= value <= maximum:
            raise HTTPException(status_code=400, detail="invalid_state_value")

    if device_type in {"temperature_sensor", "humidity_sensor"}:
        if "value" in attributes and not _is_finite_number(attributes["value"]):
            raise HTTPException(status_code=400, detail="invalid_state_value")


@router.get("")
def list_states(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id ORDER BY d.id"
        ).fetchall()
    return [build_state(dict(row)) for row in rows]


@router.get("/{entity_id}")
def get_state(entity_id: str, user: dict = Depends(get_current_user)):
    parsed = parse_entity_id(entity_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="无效的 entity_id 格式")

    with get_db() as conn:
        row = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id "
            "WHERE d.id = ? AND d.type = ?",
            (parsed[1], parsed[0]),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return build_state(dict(row))


@router.post("/{entity_id}")
def set_state(entity_id: str, req: StateUpdateRequest, user: dict = Depends(get_current_user)):
    parsed = parse_entity_id(entity_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="无效的 entity_id 格式")

    device_id = parsed[1]

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM devices WHERE id = ? AND type = ?",
            (device_id, parsed[0]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")

        device = dict(row)
        status = json.loads(device.get("status_json") or "{}")

        if req.state is not None:
            if device["type"] in {"light", "ac", "humidifier", "smart_plug"}:
                status["power"] = req.state
            elif device["type"] == "door_lock":
                status["locked"] = req.state == "locked"
            elif device["type"] in {"temperature_sensor", "humidity_sensor"}:
                try:
                    value = float(req.state)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail="invalid_state_value") from exc
                if not math.isfinite(value):
                    raise HTTPException(status_code=400, detail="invalid_state_value")
                status["value"] = value
            elif device["type"] == "pir_sensor":
                status["presence"] = req.state == "on"
            elif device["type"] == "curtain":
                try:
                    position = int(req.state)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail="invalid_state_value") from exc
                if not 0 <= position <= 100:
                    raise HTTPException(status_code=400, detail="invalid_state_value")
                status["position"] = position

        if req.attributes is not None:
            _validate_state_attributes(device["type"], req.attributes)
            for key, value in req.attributes.items():
                if key not in META_ATTRIBUTE_KEYS:
                    status[key] = value

        try:
            serialized_status = json.dumps(status, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="invalid_state_value") from exc

        conn.execute(
            "UPDATE devices SET status_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (serialized_status, device_id),
        )
        updated = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,),
        ).fetchone()

    try:
        refresh_device_state(device_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "state_projection_refresh_failed",
                "committed": True,
            },
        ) from exc
    return build_state(dict(updated)) if updated else None


@router.post("/{entity_id}/command")
def call_service(entity_id: str, req: ServiceCallRequest, user: dict = Depends(get_current_user)):
    if req.entity_id != entity_id:
        raise HTTPException(status_code=400, detail="URL 与请求体中的 entity_id 不一致")

    result = execute_entity_command(entity_id, req.action, req.params, user)
    changed_state = result["changed_state"]
    return {
        "changed_states": [changed_state] if changed_state else [],
        "service_response": {
            entity_id: {
                "topic": result["topic"],
                "action": result["payload"]["action"],
                "payload": result["payload"],
            }
        },
    }
