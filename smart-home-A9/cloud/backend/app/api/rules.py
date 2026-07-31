"""
Automation rule CRUD and options endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.services.device_command import SUPPORTED_ACTIONS_BY_DEVICE_TYPE
from app.services.rule_payloads import (
    RulePayloadError,
    normalize_action_json,
    normalize_condition_json,
)

router = APIRouter(prefix="/api/rules", tags=["automation_rules"])


TRIGGER_FIELD_BY_DEVICE_TYPE = {
    "temperature_sensor": "value",
    "humidity_sensor": "value",
    "pir_sensor": "presence",
}


def _reload_rule_runtime_after_commit() -> None:
    from app.services.rule_engine import rule_engine

    try:
        rule_engine.reload_rules()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "rule_runtime_reload_failed",
                "committed": True,
            },
        ) from exc


class RuleCreate(BaseModel):
    name: str
    condition_json: str
    action_json: str
    enabled: int = 1


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    condition_json: Optional[str] = None
    action_json: Optional[str] = None
    enabled: Optional[int] = None


@router.get("")
def list_rules(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM automation_rules ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@router.post("")
def create_rule(req: RuleCreate, user: dict = Depends(get_current_user)):
    rule_name = req.name.strip()
    if not rule_name:
        raise HTTPException(status_code=400, detail="rule_name_required")

    try:
        condition_json = normalize_condition_json(req.condition_json)
        action_json = normalize_action_json(req.action_json)
    except RulePayloadError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc

    with get_db() as conn:
        conn.execute(
            "INSERT INTO automation_rules (name, condition_json, action_json, enabled) VALUES (?, ?, ?, ?)",
            (rule_name, condition_json, action_json, req.enabled),
        )
        rule_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    _reload_rule_runtime_after_commit()
    return {"id": rule_id, "name": rule_name, "enabled": req.enabled}


@router.get("/options")
def get_rule_options(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.name, d.type, r.name AS room_name
            FROM devices d
            JOIN rooms r ON r.id = d.room_id
            ORDER BY d.id
            """
        ).fetchall()

    trigger_types_seen: set[str] = set()
    triggers = []
    targets = []
    actions: dict[str, list[str]] = {}

    for row in rows:
        device = dict(row)
        device_type = device["type"]

        trigger_field = TRIGGER_FIELD_BY_DEVICE_TYPE.get(device_type)
        if trigger_field and device_type not in trigger_types_seen:
            trigger_types_seen.add(device_type)
            triggers.append(
                {
                    "label": device["name"],
                    "value": device_type,
                    "field": trigger_field,
                    "room_name": device["room_name"],
                }
            )

        supported_actions = SUPPORTED_ACTIONS_BY_DEVICE_TYPE.get(device_type)
        if supported_actions:
            actions.setdefault(device_type, list(supported_actions))
            targets.append(
                {
                    "device_id": device["id"],
                    "label": device["name"],
                    "type": device_type,
                    "room_name": device["room_name"],
                    "actions": list(supported_actions),
                }
            )

    operators = [
        {"label": "等于", "value": "eq"},
        {"label": "不等于", "value": "neq"},
        {"label": "大于", "value": "gt"},
        {"label": "大于等于", "value": "gte"},
        {"label": "小于", "value": "lt"},
        {"label": "小于等于", "value": "lte"},
    ]

    return {
        "triggers": triggers,
        "operators": operators,
        "actions": actions,
        "targets": targets,
    }


@router.put("/{rule_id}")
def update_rule(rule_id: int, req: RuleUpdate, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="rule_not_found")

        updates = {key: value for key, value in req.model_dump().items() if value is not None}
        if "name" in updates:
            updates["name"] = updates["name"].strip()
            if not updates["name"]:
                raise HTTPException(status_code=400, detail="rule_name_required")
        try:
            if "condition_json" in updates:
                updates["condition_json"] = normalize_condition_json(updates["condition_json"])
            if "action_json" in updates:
                updates["action_json"] = normalize_action_json(updates["action_json"])
        except RulePayloadError as exc:
            raise HTTPException(status_code=400, detail=exc.code) from exc
        if not updates:
            return dict(rule)

        set_clause = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [rule_id]
        conn.execute(f"UPDATE automation_rules SET {set_clause} WHERE id = ?", values)

    _reload_rule_runtime_after_commit()
    return {"id": rule_id, **updates}


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="rule_not_found")

        conn.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))

    _reload_rule_runtime_after_commit()
    return {"message": "删除成功"}


@router.post("/{rule_id}/toggle")
def toggle_rule(rule_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="rule_not_found")

        new_enabled = 0 if rule["enabled"] else 1
        conn.execute("UPDATE automation_rules SET enabled = ? WHERE id = ?", (new_enabled, rule_id))

    _reload_rule_runtime_after_commit()
    return {"id": rule_id, "enabled": new_enabled}
