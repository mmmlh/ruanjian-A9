"""
Dashboard summary endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.services.device_view import present_device

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rooms = [
            dict(row)
            for row in conn.execute(
                """
                SELECT r.*, COUNT(d.id) AS device_count
                FROM rooms r
                LEFT JOIN devices d ON d.room_id = r.id
                GROUP BY r.id
                ORDER BY r.id
                """
            ).fetchall()
        ]
        devices = [
            dict(row)
            for row in conn.execute(
                """
                SELECT d.*, r.name AS room_name
                FROM devices d
                JOIN rooms r ON r.id = d.room_id
                ORDER BY d.id
                """
            ).fetchall()
        ]
        scenes = [dict(row) for row in conn.execute("SELECT * FROM scenes ORDER BY id").fetchall()]
        device_logs = [
            dict(row)
            for row in conn.execute("SELECT * FROM device_log ORDER BY timestamp DESC, id DESC LIMIT 8").fetchall()
        ]
        activity_logs = [
            dict(row)
            for row in conn.execute("SELECT * FROM activity_log ORDER BY timestamp DESC, id DESC LIMIT 8").fetchall()
        ]

    recent_logs = []
    for item in device_logs:
        item["event_type"] = "device"
        item["title"] = item.get("action", "")
        item["source"] = "device_log"
        recent_logs.append(item)
    recent_logs.extend(activity_logs)
    recent_logs.sort(key=lambda item: (item.get("timestamp", ""), item.get("id", 0)), reverse=True)
    recent_logs = recent_logs[:8]

    now = datetime.now(timezone.utc)
    devices = [present_device(device, now=now) for device in devices]
    online_devices = sum(1 for device in devices if device["online"])
    offline_devices = len(devices) - online_devices

    stats = {
        "total_devices": len(devices),
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "total_rooms": len(rooms),
        "total_scenes": len(scenes),
    }
    return {
        "rooms": rooms,
        "devices": devices,
        "stats": stats,
        "scenes": scenes,
        "recent_logs": recent_logs,
    }
