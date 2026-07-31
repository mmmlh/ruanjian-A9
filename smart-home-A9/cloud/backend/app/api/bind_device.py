"""
Bind a discovered candidate into a real room-bound device row.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api import discovery as discovery_api
from app.api.auth import get_current_user
from app.database.connection import get_connection
from app.services.discovery_catalog import (
    CandidateAlreadyBoundError,
    CandidateNotFoundError,
    canonical_last_seen_at,
    create_bound_device,
    summarize_candidate_status,
)
from app.services.rule_engine import rule_engine

router = APIRouter(prefix="/api/bind_device", tags=["device_binding"])


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


class BindDeviceRequest(BaseModel):
    device_id: str
    room_id: int
    name: Optional[str] = None


@router.post("")
def bind_device(req: BindDeviceRequest, user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        # Reserve the SQLite write transaction up front so room validation,
        # candidate lookup, and insert observe one coherent state.
        conn.execute("BEGIN IMMEDIATE")

        room = conn.execute("SELECT id, name FROM rooms WHERE id = ?", (req.room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="room_not_found")

        device = create_bound_device(
            conn,
            req.device_id,
            req.room_id,
            req.name,
            allowed_rooms=discovery_api.get_allowed_candidate_rooms(),
        )
        conn.commit()
    except CandidateNotFoundError as exc:
        conn.rollback()
        raise HTTPException(status_code=404, detail="candidate_not_found") from exc
    except CandidateAlreadyBoundError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="candidate_already_bound") from exc
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _reload_device_runtime_after_commit()
    device["status_summary"] = summarize_candidate_status(
        device["type"],
        device.get("status", {}),
    )
    device["last_seen_at"] = canonical_last_seen_at(
        device.get("updated_at") or device.get("created_at")
    )

    return {
        "success": True,
        "device": device,
        "message": f"设备“{device['name']}”已绑定到“{room['name']}”",
    }
