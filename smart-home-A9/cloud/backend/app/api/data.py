"""
历史数据查询：传感器数据 + 设备操作日志
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.database.connection import get_db
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/data", tags=["历史数据"])


@router.get("/sensors")
def get_sensor_data(
    device_id: Optional[int] = None,
    data_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(100, le=1000),
    user: dict = Depends(get_current_user),
):
    """传感器历史数据"""
    query = "SELECT * FROM sensor_data WHERE 1=1"
    params = []
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    if data_type:
        query += " AND data_type = ?"
        params.append(data_type)
    if start:
        query += " AND timestamp >= ?"
        params.append(start)
    if end:
        query += " AND timestamp <= ?"
        params.append(end)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/logs")
def get_device_logs(
    device_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(100, le=1000),
    user: dict = Depends(get_current_user),
):
    """设备操作日志"""
    query = "SELECT * FROM device_log WHERE 1=1"
    params = []
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if start:
        query += " AND timestamp >= ?"
        params.append(start)
    if end:
        query += " AND timestamp <= ?"
        params.append(end)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
