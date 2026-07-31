from app.services.device_view import present_device


META_ATTRIBUTE_KEYS = {
    "device_id",
    "room_id",
    "friendly_name",
    "room_name",
    "mqtt_topic",
    "brand",
    "online",
    "status_summary",
}


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_entity_id(entity_id: str) -> tuple[str, int] | None:
    parts = entity_id.split(".device_")
    if len(parts) != 2:
        return None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None


def derive_state(device_type: str, status: dict) -> str:
    if device_type in {"light", "humidifier", "smart_plug"}:
        return status.get("power", "off")
    if device_type == "ac":
        power = status.get("power", "off")
        if power == "off":
            return "off"
        return status.get("mode") or "on"
    if device_type == "door_lock":
        return "locked" if status.get("locked", True) else "unlocked"
    if device_type in {"temperature_sensor", "humidity_sensor"}:
        value = status.get("value")
        return str(value) if value is not None else "unknown"
    if device_type == "pir_sensor":
        return "on" if status.get("presence") else "off"
    if device_type == "curtain":
        position = _safe_int(status.get("position"))
        if position is None:
            return "unknown"
        if position == 0:
            return "closed"
        if position >= 100:
            return "open"
        return str(position)
    return "unknown"


def build_state(device: dict) -> dict:
    presented = present_device(device, include_status=True)
    status = presented["status"]
    entity_id = f"{presented['type']}.device_{presented['id']}"
    attributes = dict(status)
    attributes["device_id"] = presented["id"]
    attributes["room_id"] = presented["room_id"]
    attributes["friendly_name"] = presented["name"]
    attributes["room_name"] = presented.get("room_name", "")
    attributes["mqtt_topic"] = presented["mqtt_topic"]
    attributes["online"] = presented["online"]
    attributes["status_summary"] = presented["status_summary"]
    if presented.get("brand"):
        attributes["brand"] = presented["brand"]
    last_changed = presented.get("updated_at") or presented.get("created_at") or ""
    return {
        "attributes": attributes,
        "entity_id": entity_id,
        "last_changed": last_changed,
        "last_updated": last_changed,
        "state": derive_state(presented["type"], status),
    }
