"""
Discovery endpoints that return bindable candidate devices without mutating devices.
"""
from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.services.discovery_catalog import list_unbound_candidates

router = APIRouter(prefix="/api/discovery", tags=["device_discovery"])

@router.post("")
def discover(user: dict = Depends(get_current_user)):
    discovered = list_unbound_candidates()
    return {
        "discovered": discovered,
        "count": len(discovered),
        "source": "mqtt_announcements",
        "mutates_devices": False,
    }
