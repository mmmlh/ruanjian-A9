"""
联动规则 API 测试
"""
import json

import pytest

import app.services.device_command as device_command_service
import app.services.rule_engine as rule_engine_service
from app.main import on_mqtt_message
from app.services.rule_engine import rule_engine


def assert_command_messages(published, expected):
    assert len(published) == len(expected)
    for (topic, payload), (expected_topic, expected_payload) in zip(published, expected):
        assert topic == expected_topic
        assert payload.get("command_id")
        assert {key: value for key, value in payload.items() if key != "command_id"} == expected_payload


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

    @pytest.mark.parametrize("device_id", [True, False, 0, -1])
    def test_create_rule_rejects_non_positive_integer_device_id(
        self,
        client,
        auth_headers,
        device_id,
    ):
        response = client.post(
            "/api/rules",
            json={
                "name": "invalid device target",
                "condition_json": json.dumps(
                    {
                        "trigger": "pir_sensor",
                        "field": "presence",
                        "operator": "eq",
                        "value": True,
                    }
                ),
                "action_json": json.dumps(
                    [
                        {
                            "device_type": "light",
                            "device_id": device_id,
                            "action": "on",
                            "params": {},
                        }
                    ]
                ),
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_action_json"

    def test_create_rule_accepts_positive_integer_device_id(self, client, auth_headers):
        response = client.post(
            "/api/rules",
            json={
                "name": "explicit device target",
                "condition_json": json.dumps(
                    {
                        "trigger": "pir_sensor",
                        "field": "presence",
                        "operator": "eq",
                        "value": True,
                    }
                ),
                "action_json": json.dumps(
                    [
                        {
                            "device_type": "light",
                            "device_id": 4,
                            "action": "on",
                            "params": {},
                        }
                    ]
                ),
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "explicit device target"

    def test_update_rule_rejects_invalid_action_json(self, client, auth_headers):
        response = client.put(
            "/api/rules/1",
            json={"action_json": '{"device_type":"light","action":"on"}'},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_action_json"


def _replace_enabled_rules(db, action: dict, condition: dict | None = None):
    if condition is None:
        condition = {
            "trigger": "pir_sensor",
            "field": "presence",
            "operator": "eq",
            "value": True,
        }
    db.execute("UPDATE automation_rules SET enabled = 0")
    db.execute(
        "INSERT INTO automation_rules (name, condition_json, action_json, enabled) "
        "VALUES (?, ?, ?, 1)",
        (
            "projection integration rule",
            json.dumps(condition),
            json.dumps([action]),
        ),
    )
    db.commit()


class TestRuleStateIntegration:
    def test_sqlite_preloaded_and_condition_triggers_command_with_all_logs(
        self,
        client,
        db,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            ('{"power":"off","brightness":0}',),
        )
        db.execute("DELETE FROM device_log")
        db.execute("DELETE FROM activity_log")
        db.commit()
        rule_engine.reload_rules()

        rule_engine.on_sensor_data(
            "home/livingroom/pir_sensor/sensor",
            {"presence": True},
        )

        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": published[0][1]["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 80},
            },
        )
        from app.services.device_state_projection import device_state_projection

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        device_log = db.execute(
            "SELECT action, user_id FROM device_log WHERE device_id = 4"
        ).fetchone()
        activity = db.execute(
            "SELECT source FROM activity_log WHERE event_type = 'rule'"
        ).fetchone()
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "on", "brightness": 80})
        ])
        assert stored == {"power": "on", "brightness": 80}
        assert device_state_projection.get(4) == stored
        assert tuple(device_log) == ("on", None)
        assert activity["source"] == "rules.trigger"

    def test_explicit_device_id_targets_second_light_in_same_room(
        self,
        client,
        db,
        monkeypatch,
    ):
        cursor = db.execute(
            "INSERT INTO devices (room_id, type, name, mqtt_topic, status_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                1,
                "light",
                "Secondary light",
                "home/livingroom/secondary_light",
                '{"power":"off","brightness":0}',
            ),
        )
        target_id = cursor.lastrowid
        _replace_enabled_rules(
            db,
            {
                "device_id": target_id,
                "device_type": "light",
                "action": "on",
                "params": {"brightness": 18},
            },
        )
        published = []

        def record_publish(topic, payload):
            published.append((topic, json.loads(payload)))

        monkeypatch.setattr(device_command_service, "publish_message", record_publish)
        monkeypatch.setattr(rule_engine_service.mqtt_client, "publish_message", record_publish)
        rule_engine.reload_rules()

        rule_engine.on_sensor_data(
            "home/livingroom/pir_sensor/sensor",
            {"presence": True},
        )

        on_mqtt_message(
            "home/livingroom/secondary_light/ack",
            {
                "command_id": published[0][1]["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 18},
            },
        )
        main_status = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        target_status = json.loads(
            db.execute(
                "SELECT status_json FROM devices WHERE id = ?", (target_id,)
            ).fetchone()["status_json"]
        )
        assert_command_messages(published, [
            (
                "home/livingroom/secondary_light/command",
                {"action": "on", "brightness": 18},
            )
        ])
        assert main_status["power"] == "off"
        assert target_status == {"power": "on", "brightness": 18}
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = ?", (target_id,)
        ).fetchone()[0] == 1

    def test_explicit_device_id_type_mismatch_does_not_fall_back(
        self,
        client,
        db,
        monkeypatch,
    ):
        _replace_enabled_rules(
            db,
            {
                "device_id": 5,
                "device_type": "light",
                "action": "on",
                "params": {},
            },
        )
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        monkeypatch.setattr(
            rule_engine_service.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        rule_engine.reload_rules()

        rule_engine.on_sensor_data(
            "home/livingroom/pir_sensor/sensor",
            {"presence": True},
        )

        assert published == []
        assert json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )["power"] == "off"
        assert db.execute("SELECT COUNT(*) FROM device_log").fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM activity_log WHERE event_type = 'rule'"
        ).fetchone()[0] == 0

    @pytest.mark.parametrize("device_id", [True, False, 0, -1])
    def test_execute_actions_rejects_invalid_explicit_device_id_without_fallback(
        self,
        client,
        monkeypatch,
        device_id,
    ):
        from app.services.rule_payloads import RulePayloadError

        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        monkeypatch.setattr(
            rule_engine_service.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )

        with pytest.raises(RulePayloadError) as exc_info:
            rule_engine._execute_actions(
                [
                    {
                        "device_type": "light",
                        "device_id": device_id,
                        "action": "on",
                        "params": {},
                    }
                ],
                "livingroom",
            )

        assert exc_info.value.code == "invalid_action_json"
        assert published == []

    def test_unmapped_historical_target_only_publishes_mqtt(
        self,
        client,
        db,
        monkeypatch,
    ):
        _replace_enabled_rules(
            db,
            {
                "device_type": "light",
                "room_id": "garage",
                "action": "on",
                "params": {"brightness": 12},
            },
        )
        before_statuses = db.execute(
            "SELECT id, status_json FROM devices ORDER BY id"
        ).fetchall()
        before_logs = db.execute("SELECT COUNT(*) FROM device_log").fetchone()[0]
        before_activity = db.execute(
            "SELECT COUNT(*) FROM activity_log WHERE event_type = 'rule'"
        ).fetchone()[0]
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: pytest.fail("unmapped target used command service"),
        )
        monkeypatch.setattr(
            rule_engine_service.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        rule_engine.reload_rules()

        rule_engine.on_sensor_data(
            "home/livingroom/pir_sensor/sensor",
            {"presence": True},
        )

        after_statuses = db.execute(
            "SELECT id, status_json FROM devices ORDER BY id"
        ).fetchall()
        assert published == [
            ("home/garage/light/command", {"action": "on", "brightness": 12})
        ]
        assert [tuple(row) for row in after_statuses] == [
            tuple(row) for row in before_statuses
        ]
        assert db.execute("SELECT COUNT(*) FROM device_log").fetchone()[0] == before_logs
        assert db.execute(
            "SELECT COUNT(*) FROM activity_log WHERE event_type = 'rule'"
        ).fetchone()[0] == before_activity + 1

    def test_device_replacement_reloads_legacy_target_without_rule_reload(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        from app.services.device_state_projection import device_state_projection

        _replace_enabled_rules(
            db,
            {
                "device_type": "light",
                "action": "on",
                "params": {"brightness": 64},
            },
        )
        rule_engine.reload_rules()
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        deleted = client.delete("/api/devices/4", headers=auth_headers)
        assert deleted.status_code == 200
        assert device_state_projection.get(4) is None

        created = client.post(
            "/api/devices",
            json={
                "room_id": 1,
                "type": "light",
                "name": "Replacement light",
                "mqtt_topic": "home/livingroom/light",
            },
            headers=auth_headers,
        )
        assert created.status_code == 200
        replacement_id = created.json()["id"]
        assert replacement_id != 4
        assert device_state_projection.get(replacement_id) == {}

        rule_engine.on_sensor_data(
            "home/livingroom/pir_sensor/sensor",
            {"presence": True},
        )

        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": published[0][1]["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 64},
            },
        )
        stored = json.loads(
            db.execute(
                "SELECT status_json FROM devices WHERE id = ?",
                (replacement_id,),
            ).fetchone()["status_json"]
        )
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "on", "brightness": 64})
        ])
        assert stored == {"power": "on", "brightness": 64}
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = ?",
            (replacement_id,),
        ).fetchone()[0] == 1

    def test_unmapped_rule_params_cannot_override_validated_action(
        self,
        client,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            rule_engine_service.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        rule_engine._execute_actions(
            [
                {
                    "device_type": "light",
                    "room_id": "garage",
                    "action": "on",
                    "params": {"action": "off", "brightness": 12},
                }
            ],
            "livingroom",
        )

        assert published == [
            ("home/garage/light/command", {"action": "on", "brightness": 12})
        ]

    def test_rule_reload_failure_preserves_runtime_snapshot_and_reports_commit(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        from app.services.device_state_projection import device_state_projection

        previous_rules = [dict(rule) for rule in rule_engine._rules]
        previous_device_map = dict(rule_engine._device_id_map)
        previous_light_state = device_state_projection.get(4)
        monkeypatch.setattr(
            device_state_projection,
            "rebuild",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("projection reload failed")
            ),
        )
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)

        response = client.post(
            "/api/rules",
            json={
                "name": "Committed but not loaded",
                "condition_json": json.dumps(
                    {
                        "trigger": "temperature_sensor",
                        "field": "value",
                        "operator": "gt",
                        "value": 30,
                    }
                ),
                "action_json": json.dumps(
                    [
                        {
                            "device_id": 4,
                            "device_type": "light",
                            "action": "on",
                            "params": {},
                        }
                    ]
                ),
                "enabled": 1,
            },
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "rule_runtime_reload_failed",
            "committed": True,
        }
        assert db.execute(
            "SELECT 1 FROM automation_rules WHERE name = ?",
            ("Committed but not loaded",),
        ).fetchone() is not None
        assert rule_engine._rules == previous_rules
        assert rule_engine._device_id_map == previous_device_map
        assert device_state_projection.get(4) == previous_light_state
