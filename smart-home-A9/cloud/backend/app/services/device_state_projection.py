import copy
import json
import logging
import threading
from collections.abc import Callable, Mapping
from typing import Any

from app.database.connection import get_db


logger = logging.getLogger(__name__)


def load_device_state(device_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT status_json FROM devices WHERE id = ?",
            (device_id,),
        ).fetchone()

    if row is None:
        return None

    try:
        state = json.loads(row["status_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        state = None
    if not isinstance(state, dict):
        logger.warning(
            "invalid device status_json for projection: device_id=%s",
            device_id,
        )
        return {}
    return state


class DeviceStateProjection:
    def __init__(self):
        self._lock = threading.Lock()
        self._states: dict[int, dict[str, Any]] = {}

    def rebuild(
        self,
        loader: Callable[[], Mapping[int, Mapping[str, Any]]],
        *,
        clear_on_failure: bool = False,
    ) -> None:
        with self._lock:
            try:
                loaded = loader()
            except Exception:
                if clear_on_failure:
                    self._states = {}
                raise
            self._states = {
                device_id: copy.deepcopy(dict(state))
                for device_id, state in loaded.items()
            }

    def update(self, device_id: int, state: Mapping[str, Any]) -> None:
        with self._lock:
            self._states[device_id] = copy.deepcopy(dict(state))

    def refresh(
        self,
        device_id: int,
        loader: Callable[[], Mapping[str, Any] | None],
    ) -> dict[str, Any] | None:
        with self._lock:
            try:
                loaded = loader()
            except Exception:
                self._states.pop(device_id, None)
                raise
            if loaded is None:
                self._states.pop(device_id, None)
                return None

            state = copy.deepcopy(dict(loaded))
            self._states[device_id] = state
            return copy.deepcopy(state)

    def clear(self) -> None:
        with self._lock:
            self._states = {}

    def get(self, device_id: int) -> dict[str, Any] | None:
        with self._lock:
            state = self._states.get(device_id)
            return copy.deepcopy(state) if state is not None else None


device_state_projection = DeviceStateProjection()


def refresh_device_state(device_id: int) -> dict[str, Any] | None:
    return device_state_projection.refresh(
        device_id,
        lambda: load_device_state(device_id),
    )
