"""
Unified service call endpoint: /api/services
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.services.device_command import execute_entity_command

router = APIRouter(prefix="/api/services", tags=["服务调用"])


class ServiceCallRequest(BaseModel):
    entity_id: str
    action: str
    params: Optional[dict[str, Any]] = None


@router.post("")
def call_service(req: ServiceCallRequest, user: dict = Depends(get_current_user)):
    try:
        result = execute_entity_command(req.entity_id, req.action, req.params, user)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "service_call_failed"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": detail,
                "detail": detail,
                "entity_id": req.entity_id,
                "action": req.action,
                "changed_states": [],
                "service_response": {},
                "executed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    changed_state = result["changed_state"]
    entity_id = result["entity_id"]
    executed_action = result["action"]
    return {
        "success": True,
        "message": result["message"],
        "entity_id": entity_id,
        "action": executed_action,
        "changed_states": [changed_state] if changed_state else [],
        "service_response": {
            entity_id: {
                "topic": result["topic"],
                "action": executed_action,
                "payload": result["payload"],
            }
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
