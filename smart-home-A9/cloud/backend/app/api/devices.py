"""
设备管理 + 控制指令下发
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any

from app.services.device_view import present_device
from app.database.connection import get_db
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None


class CommandRequest(BaseModel):
    action: str
    params: Optional[dict[str, Any]] = None


@router.get("")
def list_devices(room_id: Optional[int] = None, type: Optional[str] = None,
                 user: dict = Depends(get_current_user)):
    """设备列表（可按 room_id / type 筛选）"""
    query = "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE 1=1"
    params = []
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
    """设备详情 + 当前状态"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return present_device(dict(row), include_status=True)


@router.put("/{device_id}")
def update_device(device_id: int, req: DeviceUpdate, user: dict = Depends(get_current_user)):
    """修改设备信息"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            return dict(row)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [device_id]
        conn.execute(f"UPDATE devices SET {set_clause} WHERE id = ?", values)
    return {"id": device_id, **updates}


@router.post("/{device_id}/command")
def send_command(device_id: int, req: CommandRequest, user: dict = Depends(get_current_user)):
    """发送控制指令到设备（通过 MQTT）"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="设备不存在")

        device = dict(row)
        topic = device["mqtt_topic"] + "/command"
        payload = {"action": req.action}
        if req.params:
            payload.update(req.params)

        # 记录操作日志
        conn.execute(
            "INSERT INTO device_log (device_id, action, detail, user_id) VALUES (?, ?, ?, ?)",
            (device_id, req.action, json.dumps(payload), int(user["sub"]))
        )

    # 发布到 MQTT（延迟导入避免循环依赖）
    from app.services.mqtt_client import publish_message
    publish_message(topic, json.dumps(payload))

    return {
        "success": True,
        "device_id": device_id,
        "topic": topic,
        "payload": payload,
    }
