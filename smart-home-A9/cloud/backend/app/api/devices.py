"""
Device management plus legacy command endpoint.
"""
import json
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.services.device_command import execute_device_command
from app.services.device_view import present_device
from app.services.rule_engine import rule_engine

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


def _reload_device_runtime_after_commit() -> None:
    try:
        rule_engine.reload_devices()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "device_runtime_reload_failed",
                "committed": True,
            },
        ) from exc


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None


class DeviceCreate(BaseModel):
    room_id: int
    type: str
    name: str
    brand: Optional[str] = None
    mqtt_topic: str


class CommandRequest(BaseModel):
    action: str
    params: Optional[dict[str, Any]] = None


@router.get("/commands/{command_id}")
def get_command_status(command_id: str, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT command_id, device_id, action, params_json, status, sent_at, acknowledged_at, "
            "response_json, error_code FROM device_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="command_not_found")

    command = dict(row)
    command["params"] = json.loads(command.pop("params_json"))
    response_json = command.pop("response_json")
    command["response"] = json.loads(response_json) if response_json else None
    return command


@router.get("")
def list_devices(room_id: Optional[int] = None, type: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE 1=1"
    params: list[Any] = []
    if room_id is not None:
        query += " AND d.room_id = ?"
        params.append(room_id)
    if type:
        query += " AND d.type = ?"
        params.append(type)
    query += " ORDER BY d.id"
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [present_device(dict(row)) for row in rows]


@router.get("/{device_id}")
def get_device(device_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return present_device(dict(row), include_status=True)


@router.put("/{device_id}")
def update_device(device_id: int, req: DeviceUpdate, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        updates = {key: value for key, value in req.model_dump().items() if value is not None}
        if not updates:
            return dict(row)
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [device_id]
        conn.execute(f"UPDATE devices SET {set_clause} WHERE id = ?", values)
    return {"id": device_id, **updates}


@router.post("/{device_id}/command")
def send_command(device_id: int, req: CommandRequest, user: dict = Depends(get_current_user)):
    result = execute_device_command(device_id, req.action, req.params, user)
    return {
        "success": True,
        "device_id": result["device_id"],
        "topic": result["topic"],
        "payload": result["payload"],
        "changed_state": result["changed_state"],
        "command_id": result["command_id"],
        "command_status": result["command_status"],
    }


@router.post("")
def create_device(req: DeviceCreate, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        room = conn.execute("SELECT id FROM rooms WHERE id = ?", (req.room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="房间不存在")
        try:
            conn.execute(
                "INSERT INTO devices (room_id, type, name, brand, mqtt_topic, status_json) "
                "VALUES (?, ?, ?, ?, ?, '{}')",
                (req.room_id, req.type, req.name, req.brand or "", req.mqtt_topic),
            )
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            if "devices.mqtt_topic" in str(exc):
                raise HTTPException(status_code=409, detail="mqtt_topic_already_exists") from exc
            raise
        device_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    _reload_device_runtime_after_commit()
    return {"id": device_id, "room_id": req.room_id, "type": req.type, "name": req.name, "success": True}


@router.delete("/{device_id}")
def delete_device(device_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        try:
            conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            if "FOREIGN KEY" in str(exc):
                raise HTTPException(status_code=409, detail="device_has_history") from exc
            raise
    _reload_device_runtime_after_commit()
    return {"success": True, "device_id": device_id}
