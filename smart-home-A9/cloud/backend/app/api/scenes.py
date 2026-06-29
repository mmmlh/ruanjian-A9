"""
场景管理 CRUD + 一键执行
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.database.connection import get_db
from app.api.auth import get_current_user
from app.services import mqtt_client

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
    try:
        json.loads(req.actions_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="actions_json 格式错误，需要有效 JSON")

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
            try:
                json.loads(updates["actions_json"])
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="actions_json 格式错误")

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

    try:
        actions = json.loads(scene["actions_json"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="场景动作数据格式错误")

    executed = []
    for action in actions:
        device_type = action.get("device_type")
        target_room = action.get("room_id", "livingroom")
        action_name = action.get("action")
        params = action.get("params", {})

        topic = f"home/{target_room}/{device_type}/command"
        payload = {"action": action_name}
        payload.update(params)

        mqtt_client.publish_message(topic, json.dumps(payload))
        executed.append({"topic": topic, "action": action_name})

    return {"scene": scene["name"], "executed": len(executed), "actions": executed}
