"""
Discovery endpoints that return bindable candidate devices without mutating devices.
"""
from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.services.discovery_catalog import list_unbound_candidates

router = APIRouter(prefix="/api/discovery", tags=["device_discovery"])

# Kept as a module-level value because the tests monkeypatch it directly.
ROOMS = ["livingroom", "bedroom", "study", "kitchen", "bathroom", "balcony"]


def get_allowed_candidate_rooms() -> list[str]:
    return list(ROOMS)


@router.post("")
def discover(user: dict = Depends(get_current_user)):
    discovered = list_unbound_candidates(allowed_rooms=get_allowed_candidate_rooms())
    return {
        "discovered": discovered,
        "count": len(discovered),
        "source": "candidate_catalog",
        "mutates_devices": False,
    }
