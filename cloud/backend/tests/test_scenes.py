"""
场景管理 API 测试
"""
import json

import pytest

from app.database import init_db


SCENE_ACTIONS = (
    '[{"device_type":"light","room_id":"livingroom","action":"on","params":{"brightness":80}},'
    '{"device_type":"ac","room_id":"livingroom","action":"set","params":{"power":"on","mode":"cool","temp":26}}]'
)

HOME_SCENE_ACTIONS = [
    {"device_type": "light", "room_id": "livingroom", "action": "on", "params": {"brightness": 80}},
    {"device_type": "light", "room_id": "bedroom", "action": "on", "params": {"brightness": 80}},
    {"device_type": "light", "room_id": "study", "action": "on", "params": {"brightness": 80}},
    {"device_type": "ac", "room_id": "livingroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
    {"device_type": "ac", "room_id": "bedroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
    {"device_type": "ac", "room_id": "study", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
    {"device_type": "curtain", "room_id": "livingroom", "action": "open", "params": {}},
    {"device_type": "curtain", "room_id": "study", "action": "open", "params": {}},
    {"device_type": "humidifier", "room_id": "bedroom", "action": "on", "params": {"level": 2, "target_humidity": 60}},
    {"device_type": "door_lock", "room_id": "livingroom", "action": "lock", "params": {}},
]

LEGACY_HOME_SCENE_ACTIONS = [
    {"device_type": "light", "room_id": "livingroom", "action": "on", "params": {"brightness": 80}},
    {"device_type": "ac", "room_id": "livingroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
    {"device_type": "door_lock", "room_id": "livingroom", "action": "unlock", "params": {"auth_code": "scene-trigger"}},
]

HOME_SCENE_DESCRIPTION = "到家一键启用：全屋灯光、空调、窗帘和加湿器开启，门锁保持上锁"
LEGACY_HOME_SCENE_DESCRIPTION = "到家一键开启：客厅灯亮 + 空调制冷 + 门禁解锁"


class TestScenes:
    """场景 CRUD + 执行测试"""

    def test_list_scenes(self, client, auth_headers):
        r = client.get("/api/scenes", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3  # 回家/离家/睡眠

    def test_scenes_contain_preset_names(self, client, auth_headers):
        r = client.get("/api/scenes", headers=auth_headers)
        names = [s["name"] for s in r.json()]
        assert "回家模式" in names
        assert "离家模式" in names
        assert "睡眠模式" in names

    def test_get_scene_detail(self, client, auth_headers):
        r = client.get("/api/scenes/1", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "回家模式"
        assert data["icon"] == "🏠"
        assert "actions_json" in data

    def test_home_scene_enables_all_controllable_devices(self, client, auth_headers):
        response = client.get("/api/scenes/1", headers=auth_headers)

        assert response.status_code == 200
        scene = response.json()
        assert scene["description"] == HOME_SCENE_DESCRIPTION
        assert json.loads(scene["actions_json"]) == HOME_SCENE_ACTIONS

    def test_init_db_repairs_legacy_home_scene(self, db):
        db.execute(
            "UPDATE scenes SET description = ?, actions_json = ? WHERE id = 1",
            (
                LEGACY_HOME_SCENE_DESCRIPTION,
                json.dumps(LEGACY_HOME_SCENE_ACTIONS, separators=(",", ":")),
            ),
        )
        db.commit()

        init_db()

        repaired = db.execute(
            "SELECT description, actions_json FROM scenes WHERE id = 1"
        ).fetchone()
        assert repaired["description"] == HOME_SCENE_DESCRIPTION
        assert json.loads(repaired["actions_json"]) == HOME_SCENE_ACTIONS

    def test_get_scene_not_found(self, client, auth_headers):
        r = client.get("/api/scenes/999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_scene(self, client, auth_headers):
        r = client.post("/api/scenes", json={
            "name": "影音模式",
            "icon": "🎬",
            "description": "看电影专用",
            "actions_json": SCENE_ACTIONS,
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "影音模式"
        assert "id" in data

    def test_create_scene_invalid_json(self, client, auth_headers):
        """actions_json 格式错误应拒绝"""
        r = client.post("/api/scenes", json={
            "name": "坏场景",
            "actions_json": "not valid json",
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_update_scene(self, client, auth_headers):
        r = client.put("/api/scenes/1", json={
            "name": "回家模式-Pro",
        }, headers=auth_headers)
        assert r.status_code == 200

    def test_delete_scene(self, client, auth_headers):
        # 先创建再删除
        cr = client.post("/api/scenes", json={
            "name": "待删除场景",
            "actions_json": SCENE_ACTIONS,
        }, headers=auth_headers)
        scene_id = cr.json()["id"]
        r = client.delete(f"/api/scenes/{scene_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_execute_scene(self, client, auth_headers):
        """执行场景 — MQTT 已 mock，验证返回结构"""
        r = client.post("/api/scenes/1/execute", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["scene"] == "回家模式" or data["scene"] is not None
        assert "executed" in data
        assert "actions" in data
        assert isinstance(data["actions"], list)

    def test_execute_nonexistent_scene(self, client, auth_headers):
        r = client.post("/api/scenes/999/execute", headers=auth_headers)
        assert r.status_code == 404
