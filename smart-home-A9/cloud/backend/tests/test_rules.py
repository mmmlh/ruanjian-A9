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

    def test_update_rule_rejects_missing_name(self, client, auth_headers):
        response = client.put(
            "/api/rules/1",
            json={"name": "   "},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "rule_name_required"

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

    def test_rule_options_endpoint_returns_supported_triggers_and_targets(self, client, auth_headers):
        r = client.get("/api/rules/options", headers=auth_headers)
        assert r.status_code == 200
        payload = r.json()
        assert "triggers" in payload
        assert "targets" in payload
        assert any(item["value"] == "temperature_sensor" for item in payload["triggers"])

    def test_rule_options_return_labels_actions_and_room_names(self, client, auth_headers):
        response = client.get("/api/rules/options", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["triggers"]
        assert payload["targets"]
        assert payload["operators"]
        assert all("label" in item for item in payload["triggers"])
        assert all(item.get("room_name") for item in payload["triggers"])
        assert all("actions" in item for item in payload["targets"])
        assert all(item.get("room_name") for item in payload["targets"])
        assert payload["operators"] == [
            {"label": "等于", "value": "eq"},
            {"label": "不等于", "value": "neq"},
            {"label": "大于", "value": "gt"},
            {"label": "大于等于", "value": "gte"},
            {"label": "小于", "value": "lt"},
            {"label": "小于等于", "value": "lte"},
        ]

    def test_create_rule_rejects_missing_name(self, client, auth_headers):
        response = client.post(
            "/api/rules",
            json={"name": "   ", "condition_json": "{}", "action_json": "[]", "enabled": 1},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "rule_name_required"

    def test_create_rule_rejects_invalid_condition_json(self, client, auth_headers):
        response = client.post(
            "/api/rules",
            json={
                "name": "invalid condition",
                "condition_json": '{"trigger":"pir_sensor","field":"presence"',
                "action_json": '[{"device_type":"light","action":"on","params":{}}]',
                "enabled": 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_condition_json"

    def test_create_rule_rejects_invalid_action_json(self, client, auth_headers):
        response = client.post(
            "/api/rules",
            json={
                "name": "invalid action",
                "condition_json": '{"trigger":"pir_sensor","field":"presence","operator":"eq","value":true}',
                "action_json": '{"device_type":"light","action":"on"}',
                "enabled": 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_action_json"

    def test_update_rule_rejects_invalid_action_json(self, client, auth_headers):
        response = client.put(
            "/api/rules/1",
            json={"action_json": '{"device_type":"light","action":"on"}'},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_action_json"
