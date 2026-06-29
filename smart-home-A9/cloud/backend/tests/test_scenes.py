"""
场景管理 API 测试
"""
import pytest


SCENE_ACTIONS = (
    '[{"device_type":"light","room_id":"livingroom","action":"on","params":{"brightness":80}},'
    '{"device_type":"ac","room_id":"livingroom","action":"set","params":{"power":"on","mode":"cool","temp":26}}]'
)


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
