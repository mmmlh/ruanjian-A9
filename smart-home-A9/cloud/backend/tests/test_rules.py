"""
联动规则 API 测试
"""
import pytest


class TestRules:
    """规则 CRUD + 开关测试"""

    def test_list_rules(self, client, auth_headers):
        r = client.get("/api/rules", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 4  # 种子数据有 4 条规则

    def test_create_rule(self, client, auth_headers):
        r = client.post("/api/rules", json={
            "name": "测试规则",
            "condition_json": '{"trigger":"temperature_sensor","field":"value","operator":"gt","value":30}',
            "action_json": '[{"device_type":"ac","action":"set","params":{"power":"on","mode":"cool","temp":22}}]',
            "enabled": 1,
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "测试规则"
        assert "id" in data

    def test_update_rule(self, client, auth_headers):
        r = client.put("/api/rules/1", json={
            "name": "人来开灯-已更新",
        }, headers=auth_headers)
        assert r.status_code == 200

    def test_toggle_rule(self, client, auth_headers):
        # 先获取当前状态
        r = client.get("/api/rules", headers=auth_headers)
        current = r.json()[0]["enabled"]
        r = client.post("/api/rules/1/toggle", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] == (0 if current else 1)

    def test_delete_rule(self, client, auth_headers):
        # 先创建再删除
        cr = client.post("/api/rules", json={
            "name": "待删除",
            "condition_json": '{"trigger":"pir_sensor","field":"presence","operator":"eq","value":true}',
            "action_json": '[{"device_type":"light","action":"on","params":{}}]',
        }, headers=auth_headers)
        rule_id = cr.json()["id"]
        r = client.delete(f"/api/rules/{rule_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_nonexistent(self, client, auth_headers):
        r = client.delete("/api/rules/999", headers=auth_headers)
        assert r.status_code == 404
