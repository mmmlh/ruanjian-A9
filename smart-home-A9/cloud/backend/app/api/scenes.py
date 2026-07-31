"""
场景管理 CRUD + 一键执行
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Optional

from app.database.connection import get_db
from app.api.auth import get_current_user
from app.services import mqtt_client
from app.services.activity_log import write_activity
from app.services.device_command import (
    execute_device_command,
    normalize_and_validate_command,
)

router = APIRouter(prefix="/api/scenes", tags=["场景管理"])


class SceneCreate(BaseModel):
    name: str
    icon: str = "🏠"
    description: Optional[str] = None
    actions_json: str  # JSON 字符串: [{"device_type":"light","room_id":"livingroom","action":"on","params":{}}]


class SceneUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    actions_json: Optional[str] = None


def _parse_scene_action_structures(
    raw: str,
    status_code: int,
) -> list[dict[str, Any]]:
    try:
        actions = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=status_code, detail="invalid_scene_actions") from exc

    if not isinstance(actions, list):
        raise HTTPException(status_code=status_code, detail="invalid_scene_actions")

    parsed_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")

        device_type = action.get("device_type")
        device_id = action.get("device_id")
        action_name = action.get("action")
        params = action.get("params", {})
        has_device_type = isinstance(device_type, str) and bool(device_type.strip())
        has_device_id = (
            isinstance(device_id, int)
            and not isinstance(device_id, bool)
            and device_id > 0
        )
        if "device_type" in action and not has_device_type:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
        if "device_id" in action and not has_device_id:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
        if has_device_type and has_device_id:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
        if not has_device_type and not has_device_id:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
        if not isinstance(action_name, str) or not action_name.strip():
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
        if not isinstance(params, dict):
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")

        room_id = action.get("room_id")
        if "room_id" in action and (not isinstance(room_id, str) or not room_id.strip()):
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions")

        parsed_action = dict(action)
        parsed_action.pop("_mqtt_topic", None)
        if has_device_type:
            parsed_action["device_type"] = device_type.strip()
        if "room_id" in action:
            parsed_action["room_id"] = room_id.strip()
        parsed_actions.append(parsed_action)

    return parsed_actions


def _load_scene_devices() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, type, mqtt_topic FROM devices").fetchall()
    return [dict(row) for row in rows]


def _normalize_scene_actions(
    actions: list[dict[str, Any]],
    devices_by_id: dict[int, dict[str, Any]],
    status_code: int,
) -> list[dict[str, Any]]:
    normalized_actions: list[dict[str, Any]] = []
    for action in actions:
        device_id = action.get("device_id")
        if device_id is not None:
            device = devices_by_id.get(device_id)
            if device is None:
                raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
            device_type = device["type"]
        else:
            device_type = action["device_type"]

        try:
            canonical_action, normalized_params = normalize_and_validate_command(
                device_type,
                action["action"],
                action.get("params", {}),
            )
        except HTTPException as exc:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions") from exc

        normalized_action = dict(action)
        normalized_action["device_type"] = device_type
        normalized_action["action"] = canonical_action
        normalized_action["params"] = normalized_params
        normalized_actions.append(normalized_action)
    return normalized_actions


def parse_scene_actions(raw: str, status_code: int = 400) -> list[dict[str, Any]]:
    actions = _parse_scene_action_structures(raw, status_code)
    devices_by_id: dict[int, dict[str, Any]] = {}
    if any("device_id" in action for action in actions):
        devices_by_id = {
            device["id"]: device
            for device in _load_scene_devices()
        }
    return _normalize_scene_actions(actions, devices_by_id, status_code)


@router.get("")
def list_scenes(user: dict = Depends(get_current_user)):
    """场景列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM scenes ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_scene(req: SceneCreate, user: dict = Depends(get_current_user)):
    """创建场景"""
    # 校验 actions_json
    parse_scene_actions(req.actions_json)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO scenes (name, icon, description, actions_json) VALUES (?, ?, ?, ?)",
            (req.name, req.icon, req.description, req.actions_json),
        )
        scene_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": scene_id, "name": req.name, "icon": req.icon}


@router.get("/{scene_id}")
def get_scene(scene_id: int, user: dict = Depends(get_current_user)):
    """场景详情"""
    with get_db() as conn:
        scene = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if scene is None:
            raise HTTPException(status_code=404, detail="场景不存在")
    return dict(scene)


@router.put("/{scene_id}")
def update_scene(scene_id: int, req: SceneUpdate, user: dict = Depends(get_current_user)):
    """更新场景"""
    with get_db() as conn:
        scene = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if scene is None:
            raise HTTPException(status_code=404, detail="场景不存在")

        updates = {k: v for k, v in req.model_dump().items() if v is not None}

        # 校验 actions_json
        if "actions_json" in updates:
            parse_scene_actions(updates["actions_json"])

        if not updates:
            return dict(scene)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [scene_id]
        conn.execute(f"UPDATE scenes SET {set_clause} WHERE id = ?", values)
    return {"id": scene_id, **updates}


@router.delete("/{scene_id}")
def delete_scene(scene_id: int, user: dict = Depends(get_current_user)):
    """删除场景"""
    with get_db() as conn:
        scene = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if scene is None:
            raise HTTPException(status_code=404, detail="场景不存在")
        conn.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
    return {"message": "删除成功"}


@router.post("/{scene_id}/execute")
def execute_scene(scene_id: int, user: dict = Depends(get_current_user)):
    """一键执行场景 — 通过 MQTT 下发所有动作指令"""
    with get_db() as conn:
        scene = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if scene is None:
            raise HTTPException(status_code=404, detail="场景不存在")

    parsed_actions = _parse_scene_action_structures(
        scene["actions_json"],
        status_code=409,
    )
    devices = _load_scene_devices()
    devices_by_id = {device["id"]: device for device in devices}
    devices_by_topic = {device["mqtt_topic"]: device for device in devices}
    actions = _normalize_scene_actions(parsed_actions, devices_by_id, status_code=409)

    targets: list[tuple[dict[str, Any], dict[str, Any] | None, str]] = []
    for action in actions:
        if "device_id" in action:
            device = devices_by_id[action["device_id"]]
            mqtt_topic = device["mqtt_topic"]
        else:
            target_room = action.get("room_id", "livingroom")
            mqtt_topic = f"home/{target_room}/{action['device_type']}"
            device = devices_by_topic.get(mqtt_topic)
        targets.append((action, device, f"{mqtt_topic}/command"))

    executed = []
    for index, (action, device, topic) in enumerate(targets):
        action_name = action["action"]
        params = action["params"]
        try:
            if device is not None:
                result = execute_device_command(
                    device["id"],
                    action_name,
                    params,
                    user,
                    expected_device_type=action["device_type"],
                )
                topic = result["topic"]
                action_name = result["action"]
            else:
                payload = {**params, "action": action_name}
                mqtt_client.publish_message(topic, json.dumps(payload))
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "scene_partial_failure",
                    "executed": len(executed),
                    "failed_index": index,
                },
            ) from exc
        executed.append({"topic": topic, "action": action_name})

    write_activity(
        event_type="scene",
        title=scene["name"],
        detail=json.dumps({"executed": len(executed)}, ensure_ascii=False),
        source="scenes.execute",
        user_id=int(user["sub"]),
    )

    return {"scene": scene["name"], "executed": len(executed), "actions": executed}
