"""
房间管理 CRUD
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.database.connection import get_db
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/rooms", tags=["房间管理"])


class RoomCreate(BaseModel):
    name: str
    floor: int = 1
    description: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    floor: Optional[int] = None
    description: Optional[str] = None


@router.get("")
def list_rooms(user: dict = Depends(get_current_user)):
    """获取房间列表（含设备数量）"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.*, COUNT(d.id) as device_count
            FROM rooms r LEFT JOIN devices d ON d.room_id = r.id
            GROUP BY r.id ORDER BY r.id
        """).fetchall()
    return [dict(r) for r in rows]


@router.get("/{room_id}")
def get_room(room_id: int, user: dict = Depends(get_current_user)):
    """获取房间详情（含设备实时状态）"""
    with get_db() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="房间不存在")
        devices = conn.execute(
            "SELECT * FROM devices WHERE room_id = ?", (room_id,)
        ).fetchall()
    result = dict(room)
    result["devices"] = [dict(d) for d in devices]
    return result


@router.post("")
def create_room(req: RoomCreate, user: dict = Depends(get_current_user)):
    """添加房间"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO rooms (name, floor, description) VALUES (?, ?, ?)",
            (req.name, req.floor, req.description)
        )
        room_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": room_id, "name": req.name, "floor": req.floor, "description": req.description}


@router.put("/{room_id}")
def update_room(room_id: int, req: RoomUpdate, user: dict = Depends(get_current_user)):
    """修改房间信息"""
    with get_db() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="房间不存在")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            return dict(room)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [room_id]
        conn.execute(f"UPDATE rooms SET {set_clause} WHERE id = ?", values)
    return {"id": room_id, **updates}


@router.delete("/{room_id}")
def delete_room(room_id: int, user: dict = Depends(get_current_user)):
    """删除房间"""
    with get_db() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="房间不存在")
        # 检查是否有设备
        device_count = conn.execute(
            "SELECT COUNT(*) FROM devices WHERE room_id = ?", (room_id,)
        ).fetchone()[0]
        if device_count > 0:
            raise HTTPException(status_code=400, detail=f"房间下还有 {device_count} 个设备，请先删除设备")
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    return {"message": "删除成功"}
