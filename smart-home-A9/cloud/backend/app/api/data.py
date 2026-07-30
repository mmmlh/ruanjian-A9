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
    limit: int = Query(100, ge=1, le=1000),
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
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(get_current_user),
):
    """设备操作日志"""
    entries: list[dict] = []
    device_query = "SELECT * FROM device_log WHERE 1=1"
    device_params = []
    if device_id:
        device_query += " AND device_id = ?"
        device_params.append(device_id)
    if user_id:
        device_query += " AND user_id = ?"
        device_params.append(user_id)
    if start:
        device_query += " AND timestamp >= ?"
        device_params.append(start)
    if end:
        device_query += " AND timestamp <= ?"
        device_params.append(end)
    device_query += " ORDER BY timestamp DESC LIMIT ?"
    device_params.append(limit)

    activity_query = "SELECT * FROM activity_log WHERE 1=1"
    activity_params = []
    if device_id:
        activity_query += " AND device_id = ?"
        activity_params.append(device_id)
    if user_id:
        activity_query += " AND user_id = ?"
        activity_params.append(user_id)
    if start:
        activity_query += " AND timestamp >= ?"
        activity_params.append(start)
    if end:
        activity_query += " AND timestamp <= ?"
        activity_params.append(end)
    if event_type:
        activity_query += " AND event_type = ?"
        activity_params.append(event_type)
    activity_query += " ORDER BY timestamp DESC LIMIT ?"
    activity_params.append(limit)
    with get_db() as conn:
        device_rows = []
        if event_type in (None, "device"):
            device_rows = conn.execute(device_query, device_params).fetchall()
        activity_rows = conn.execute(activity_query, activity_params).fetchall()

    for row in device_rows:
        item = dict(row)
        item["event_type"] = "device"
        item["title"] = row["action"]
        item["source"] = "device_log"
        entries.append(item)

    for row in activity_rows:
        entries.append(dict(row))

    entries.sort(key=lambda item: item["timestamp"], reverse=True)
    return entries[:limit]
