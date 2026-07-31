import copy
import threading
from collections.abc import Callable, Mapping
from typing import Any


class DeviceStateProjection:
    def __init__(self):
        self._lock = threading.Lock()
        self._states: dict[int, dict[str, Any]] = {}

    def rebuild(
        self,
        loader: Callable[[], Mapping[int, Mapping[str, Any]]],
    ) -> None:
        with self._lock:
            loaded = loader()
            self._states = {
                device_id: copy.deepcopy(dict(state))
                for device_id, state in loaded.items()
            }

    def update(self, device_id: int, state: Mapping[str, Any]) -> None:
        with self._lock:
            self._states[device_id] = copy.deepcopy(dict(state))

    def get(self, device_id: int) -> dict[str, Any] | None:
        with self._lock:
            state = self._states.get(device_id)
            return copy.deepcopy(state) if state is not None else None


device_state_projection = DeviceStateProjection()
