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
from app.services.device_command import normalize_and_validate_command

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


def parse_scene_actions(raw: str, status_code: int = 400) -> list[dict[str, Any]]:
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

        mqtt_topic = None
        if has_device_type:
            validated_device_type = device_type.strip()
        else:
            with get_db() as conn:
                device = conn.execute(
                    "SELECT type, mqtt_topic FROM devices WHERE id = ?",
                    (device_id,),
                ).fetchone()
            if device is None:
                raise HTTPException(status_code=status_code, detail="invalid_scene_actions")
            validated_device_type = device["type"]
            mqtt_topic = f"{device['mqtt_topic']}/command"

        try:
            canonical_action, normalized_params = normalize_and_validate_command(
                validated_device_type,
                action_name,
                params,
            )
        except HTTPException as exc:
            raise HTTPException(status_code=status_code, detail="invalid_scene_actions") from exc

        parsed_action = dict(action)
        parsed_action.pop("_mqtt_topic", None)
        parsed_action["device_type"] = validated_device_type
        parsed_action["action"] = canonical_action
        parsed_action["params"] = normalized_params
        if "room_id" in action:
            parsed_action["room_id"] = room_id.strip()
        if mqtt_topic is not None:
            parsed_action["_mqtt_topic"] = mqtt_topic
        parsed_actions.append(parsed_action)

    return parsed_actions


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

    actions = parse_scene_actions(scene["actions_json"], status_code=409)

    executed = []
    for action in actions:
        device_type = action.get("device_type")
        target_room = action.get("room_id", "livingroom")
        action_name = action.get("action")
        params = action.get("params", {})

        topic = action.get("_mqtt_topic") or f"home/{target_room}/{device_type}/command"
        payload = {"action": action_name}
        payload.update(params)
        payload["action"] = action_name

        mqtt_client.publish_message(topic, json.dumps(payload))
        executed.append({"topic": topic, "action": action_name})

    write_activity(
        event_type="scene",
        title=scene["name"],
        detail=json.dumps({"executed": len(executed)}, ensure_ascii=False),
        source="scenes.execute",
        user_id=int(user["sub"]),
    )

    return {"scene": scene["name"], "executed": len(executed), "actions": executed}
