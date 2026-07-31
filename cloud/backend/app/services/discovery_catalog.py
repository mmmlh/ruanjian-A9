"""
Deterministic discovery-candidate catalog used by the binding flow.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from app.database.connection import get_db
from app.services.device_view import summarize_device_status


_DEFAULT_STATUS_BY_TYPE: dict[str, dict[str, Any]] = {
    "light": {"power": "off", "brightness": 0},
    "ac": {"power": "off", "mode": "cool", "temp": 26},
    "door_lock": {"locked": True},
    "temperature_sensor": {"value": 24.5, "unit": "celsius"},
    "humidity_sensor": {"value": 52.0, "unit": "percent"},
    "pir_sensor": {"presence": False},
    "curtain": {"position": 0},
    "humidifier": {"power": "off", "level": 2, "target_humidity": 60},
    "smart_plug": {"power": "off", "power_watts": 0.0, "total_kwh": 0.0},
}

_BASE_CANDIDATES: list[dict[str, Any]] = [
    {
        "id": "candidate-livingroom-ambient-light",
        "room": "livingroom",
        "room_hint": "客厅",
        "type": "light",
        "name": "客厅氛围灯",
        "brand": "",
        "mqtt_topic": "home/livingroom/light_extra",
    },
    {
        "id": "candidate-bedroom-humidifier",
        "room": "bedroom",
        "room_hint": "卧室",
        "type": "humidifier",
        "name": "卧室备用加湿器",
        "brand": "",
        "mqtt_topic": "home/bedroom/humidifier_extra",
    },
    {
        "id": "candidate-study-curtain",
        "room": "study",
        "room_hint": "书房",
        "type": "curtain",
        "name": "书房窗帘扩展",
        "brand": "",
        "mqtt_topic": "home/study/curtain_extra",
    },
]


class CandidateNotFoundError(ValueError):
    """Requested candidate is not available under the current policy/state."""


class CandidateAlreadyBoundError(ValueError):
    """Requested candidate topic is already materialized as a real device."""


def _status_for_type(device_type: str) -> dict[str, Any]:
    return dict(_DEFAULT_STATUS_BY_TYPE.get(device_type, {}))


def summarize_candidate_status(device_type: str, status: dict[str, Any]) -> str:
    return summarize_device_status(device_type, status)


def canonical_last_seen_at(value: str | None = None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    else:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)

    return parsed.isoformat()


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized["status_summary"] = summarize_candidate_status(
        normalized["type"],
        normalized.get("status", {}),
    )
    normalized["last_seen_at"] = canonical_last_seen_at(normalized.get("last_seen_at"))
    return normalized


def _load_existing_topics(conn: sqlite3.Connection) -> set[str]:
    return {
        row["mqtt_topic"]
        for row in conn.execute("SELECT mqtt_topic FROM devices").fetchall()
    }


def _build_catalog_candidates(allowed_rooms: Iterable[str] | None = None) -> list[dict[str, Any]]:
    allowed = set(allowed_rooms or [])
    candidates: list[dict[str, Any]] = []

    for candidate in _BASE_CANDIDATES:
        if allowed and candidate["room"] not in allowed:
            continue
        candidates.append(
            {
                **candidate,
                "status": _status_for_type(candidate["type"]),
                "online": True,
            }
        )

    return candidates


def _build_unbound_candidates(
    existing_topics: set[str],
    allowed_rooms: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for candidate in _build_catalog_candidates(allowed_rooms=allowed_rooms):
        if candidate["mqtt_topic"] in existing_topics:
            continue
        candidates.append(normalize_candidate(candidate))

    return candidates


def list_unbound_candidates(
    allowed_rooms: Iterable[str] | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    if conn is not None:
        return _build_unbound_candidates(_load_existing_topics(conn), allowed_rooms=allowed_rooms)

    with get_db() as managed_conn:
        return _build_unbound_candidates(_load_existing_topics(managed_conn), allowed_rooms=allowed_rooms)


def get_unbound_candidate(
    candidate_id: str,
    allowed_rooms: Iterable[str] | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    candidate = next(
        (item for item in list_unbound_candidates(allowed_rooms=allowed_rooms, conn=conn) if item["id"] == candidate_id),
        None,
    )
    if candidate is None:
        raise CandidateNotFoundError("candidate_not_found")
    return candidate


def get_catalog_candidate(
    candidate_id: str,
    allowed_rooms: Iterable[str] | None = None,
) -> dict[str, Any] | None:
    return next(
        (
            normalize_candidate(item)
            for item in _build_catalog_candidates(allowed_rooms=allowed_rooms)
            if item["id"] == candidate_id
        ),
        None,
    )


def create_bound_device(
    conn: sqlite3.Connection,
    candidate_id: str,
    room_id: int,
    custom_name: str | None = None,
    allowed_rooms: Iterable[str] | None = None,
) -> dict[str, Any]:
    candidate = get_catalog_candidate(candidate_id, allowed_rooms=allowed_rooms)
    if candidate is None:
        raise CandidateNotFoundError("candidate_not_found")

    if conn.execute("SELECT 1 FROM devices WHERE mqtt_topic = ?", (candidate["mqtt_topic"],)).fetchone():
        raise CandidateAlreadyBoundError("candidate_already_bound")

    device_name = custom_name or candidate["name"]
    try:
        conn.execute(
            """
            INSERT INTO devices (room_id, type, name, brand, mqtt_topic, status_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                room_id,
                candidate["type"],
                device_name,
                candidate["brand"],
                candidate["mqtt_topic"],
                json.dumps(candidate["status"], ensure_ascii=False),
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "devices.mqtt_topic" in str(exc) or "UNIQUE constraint failed: devices.mqtt_topic" in str(exc):
            raise CandidateAlreadyBoundError("candidate_already_bound") from exc
        raise

    device_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = conn.execute(
        """
        SELECT d.*, r.name AS room_name
        FROM devices d
        JOIN rooms r ON r.id = d.room_id
        WHERE d.id = ?
        """,
        (device_id,),
    ).fetchone()

    result = dict(row)
    result["status"] = dict(candidate["status"])
    return result
