"""Real MQTT device discovery records and atomic binding helpers."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.database.connection import get_db
from app.services.device_view import summarize_device_status


DISCOVERY_TTL_SECONDS = 90


class CandidateNotFoundError(ValueError):
    """Requested discovery record is no longer available."""


class CandidateAlreadyBoundError(ValueError):
    """Requested MQTT topic has already been bound."""


def summarize_candidate_status(device_type: str, status: dict[str, Any]) -> str:
    return summarize_device_status(device_type, status)


def canonical_last_seen_at(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    return parsed.isoformat()


def _capabilities(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _candidate_from_row(row: sqlite3.Row) -> dict[str, Any]:
    device_type = row["device_type"]
    hardware_id = row["hardware_id"]
    return {
        "id": hardware_id,
        "hardware_id": hardware_id,
        "room": row["room_hint"],
        "room_hint": row["room_hint"],
        "type": device_type,
        "name": f"{device_type.replace('_', ' ').title()} ({hardware_id})",
        "brand": "",
        "mqtt_topic": row["mqtt_topic"],
        "protocol_version": row["protocol_version"],
        "capabilities": _capabilities(row["capabilities_json"]),
        "status": {},
        "status_summary": "",
        "last_seen_at": canonical_last_seen_at(row["last_seen_at"]),
        "online": True,
    }


def list_unbound_candidates(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT d.*
        FROM discovered_devices d
        WHERE d.last_seen_at >= datetime('now', ?)
          AND NOT EXISTS (SELECT 1 FROM devices b WHERE b.mqtt_topic = d.mqtt_topic)
        ORDER BY d.last_seen_at DESC, d.hardware_id ASC
    """
    params = (f"-{DISCOVERY_TTL_SECONDS} seconds",)
    if conn is not None:
        return [_candidate_from_row(row) for row in conn.execute(query, params).fetchall()]
    with get_db() as managed_conn:
        return [_candidate_from_row(row) for row in managed_conn.execute(query, params).fetchall()]


def get_unbound_candidate(conn: sqlite3.Connection, hardware_id: str) -> dict[str, Any]:
    query = """
        SELECT d.*
        FROM discovered_devices d
        WHERE d.hardware_id = ?
          AND d.last_seen_at >= datetime('now', ?)
          AND NOT EXISTS (SELECT 1 FROM devices b WHERE b.mqtt_topic = d.mqtt_topic)
    """
    row = conn.execute(query, (hardware_id, f"-{DISCOVERY_TTL_SECONDS} seconds")).fetchone()
    if row is None:
        raise CandidateNotFoundError("candidate_not_found")
    return _candidate_from_row(row)


def create_bound_device(
    conn: sqlite3.Connection,
    candidate_id: str,
    room_id: int,
    custom_name: str | None = None,
) -> dict[str, Any]:
    discovery_row = conn.execute(
        "SELECT mqtt_topic FROM discovered_devices WHERE hardware_id = ?",
        (candidate_id,),
    ).fetchone()
    if discovery_row is not None and conn.execute(
        "SELECT 1 FROM devices WHERE mqtt_topic = ?", (discovery_row["mqtt_topic"],)
    ).fetchone():
        raise CandidateAlreadyBoundError("candidate_already_bound")

    candidate = get_unbound_candidate(conn, candidate_id)

    device_name = custom_name or candidate["name"]
    try:
        conn.execute(
            """
            INSERT INTO devices (
                room_id, type, name, brand, mqtt_topic, status_json, hardware_id,
                protocol_version, capabilities_json, last_seen_at, connection_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'online')
            """,
            (
                room_id,
                candidate["type"],
                device_name,
                candidate["brand"],
                candidate["mqtt_topic"],
                "{}",
                candidate["hardware_id"],
                candidate["protocol_version"],
                json.dumps(candidate["capabilities"], ensure_ascii=False),
                candidate["last_seen_at"],
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "mqtt_topic" in str(exc) or "UNIQUE constraint failed: devices.mqtt_topic" in str(exc):
            raise CandidateAlreadyBoundError("candidate_already_bound") from exc
        raise

    device_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = conn.execute(
        """
        SELECT d.*, r.name AS room_name
        FROM devices d JOIN rooms r ON r.id = d.room_id
        WHERE d.id = ?
        """,
        (device_id,),
    ).fetchone()
    result = dict(row)
    result["status"] = {}
    return result
