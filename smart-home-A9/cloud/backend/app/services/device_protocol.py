"""MQTT device registration, presence, acknowledgement, and timeout helpers."""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from app.database.connection import get_db


logger = logging.getLogger(__name__)
COMMAND_TIMEOUT_SECONDS = 15


def topic_root(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "home":
        return None
    return "/".join(parts[:3])


def _safe_json(value: Any) -> str | None:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return None


def _mark_present(conn, mqtt_topic: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM devices WHERE mqtt_topic = ?", (mqtt_topic,)
    ).fetchone()
    if row is None:
        return None
    conn.execute(
        "UPDATE devices SET last_seen_at = CURRENT_TIMESTAMP, connection_state = 'online' WHERE id = ?",
        (row["id"],),
    )
    return int(row["id"])


def record_hello(topic: str, payload: Mapping[str, Any]) -> int | None:
    mqtt_topic = topic_root(topic)
    hardware_id = payload.get("hardware_id")
    protocol_version = payload.get("protocol_version")
    capabilities = payload.get("capabilities")
    if (
        mqtt_topic is None
        or not isinstance(hardware_id, str)
        or not hardware_id.strip()
        or not isinstance(protocol_version, str)
        or not protocol_version.strip()
        or not isinstance(capabilities, Mapping)
    ):
        return None
    capabilities_json = _safe_json(dict(capabilities))
    if capabilities_json is None:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, hardware_id FROM devices WHERE mqtt_topic = ?", (mqtt_topic,)
        ).fetchone()
        if row is None:
            logger.warning("ignored hello from unregistered device topic %s", mqtt_topic)
            return None
        registered_hardware_id = row["hardware_id"]
        if registered_hardware_id and registered_hardware_id != hardware_id:
            logger.warning("ignored hello with mismatched hardware id for %s", mqtt_topic)
            return None
        conn.execute(
            "UPDATE devices SET hardware_id = ?, protocol_version = ?, capabilities_json = ?, "
            "last_seen_at = CURRENT_TIMESTAMP, connection_state = 'online' WHERE id = ?",
            (hardware_id, protocol_version, capabilities_json, row["id"]),
        )
        return int(row["id"])


def record_heartbeat(topic: str, payload: Mapping[str, Any]) -> int | None:
    mqtt_topic = topic_root(topic)
    hardware_id = payload.get("hardware_id")
    if mqtt_topic is None or not isinstance(hardware_id, str) or not hardware_id.strip():
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, hardware_id FROM devices WHERE mqtt_topic = ?", (mqtt_topic,)
        ).fetchone()
        if row is None or row["hardware_id"] != hardware_id:
            return None
        return _mark_present(conn, mqtt_topic)


def record_device_message(topic: str) -> int | None:
    mqtt_topic = topic_root(topic)
    if mqtt_topic is None:
        return None
    with get_db() as conn:
        return _mark_present(conn, mqtt_topic)


def reconcile_ack(topic: str, payload: Mapping[str, Any]) -> tuple[int, dict[str, Any]] | None:
    mqtt_topic = topic_root(topic)
    command_id = payload.get("command_id")
    success = payload.get("success")
    state = payload.get("state")
    if (
        mqtt_topic is None
        or not isinstance(command_id, str)
        or not command_id.strip()
        or not isinstance(success, bool)
        or not isinstance(state, Mapping)
    ):
        return None

    response_json = _safe_json(dict(payload))
    if response_json is None:
        return None
    confirmed_state = {
        key: value
        for key, value in state.items()
        if key not in {"device_id", "brand_command", "success"}
    }
    with get_db() as conn:
        command = conn.execute(
            "SELECT c.device_id, c.status, d.mqtt_topic, d.status_json FROM device_commands c "
            "JOIN devices d ON d.id = c.device_id WHERE c.command_id = ?",
            (command_id,),
        ).fetchone()
        if command is None or command["mqtt_topic"] != mqtt_topic:
            return None
        device_id = int(command["device_id"])
        if command["status"] != "pending":
            return None
        if success:
            try:
                current_state = json.loads(command["status_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                current_state = {}
            if not isinstance(current_state, dict):
                current_state = {}
            confirmed_state = {**current_state, **confirmed_state}
            state_json = _safe_json(confirmed_state)
            if state_json is None:
                return None
            conn.execute(
                "UPDATE devices SET status_json = ?, updated_at = CURRENT_TIMESTAMP, "
                "last_seen_at = CURRENT_TIMESTAMP, connection_state = 'online' WHERE id = ?",
                (state_json, device_id),
            )
            command_status = "acknowledged"
            error_code = None
        else:
            conn.execute(
                "UPDATE devices SET last_seen_at = CURRENT_TIMESTAMP, connection_state = 'online' WHERE id = ?",
                (device_id,),
            )
            command_status = "failed"
            error_code = payload.get("error_code") if isinstance(payload.get("error_code"), str) else "DEVICE_REJECTED"
        conn.execute(
            "UPDATE device_commands SET status = ?, acknowledged_at = CURRENT_TIMESTAMP, "
            "response_json = ?, error_code = ? WHERE command_id = ?",
            (command_status, response_json, error_code, command_id),
        )
        return device_id, confirmed_state


def expire_pending_commands(timeout_seconds: int = COMMAND_TIMEOUT_SECONDS) -> int:
    with get_db() as conn:
        result = conn.execute(
            "UPDATE device_commands SET status = 'timed_out', error_code = 'ACK_TIMEOUT' "
            "WHERE status = 'pending' AND sent_at <= datetime('now', ?)",
            (f"-{timeout_seconds} seconds",),
        )
        return result.rowcount
