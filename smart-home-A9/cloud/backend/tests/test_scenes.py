"""
场景管理 API 测试
"""
import json

import pytest
from fastapi import HTTPException

from app.api import scenes as scenes_api
from app.database import init_db
from app.main import on_mqtt_message
import app.services.device_command as device_command_service


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


def assert_command_messages(published, expected):
    assert len(published) == len(expected)
    for (topic, payload), (expected_topic, expected_payload) in zip(published, expected):
        assert topic == expected_topic
        assert payload.get("command_id")
        assert {key: value for key, value in payload.items() if key != "command_id"} == expected_payload


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

    @pytest.mark.parametrize("actions_json", ["123", "{}", '["bad"]'])
    def test_create_scene_rejects_non_action_lists(self, client, auth_headers, actions_json):
        response = client.post(
            "/api/scenes",
            json={"name": "Invalid scene", "actions_json": actions_json},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_scene_actions"

    @pytest.mark.parametrize(
        "action",
        [
            {"action": "on", "params": {}},
            {"device_type": "", "action": "on", "params": {}},
            {"device_type": "light", "action": "", "params": {}},
            {"device_type": "light", "action": "on", "params": []},
            {"device_type": "light", "room_id": "", "action": "on", "params": {}},
            {"device_type": "light", "action": "destroy", "params": {}},
            {"device_id": 0, "action": "on", "params": {}},
            {"device_id": True, "action": "on", "params": {}},
            {"device_type": "light", "device_id": 5, "action": "on", "params": {}},
        ],
    )
    def test_create_scene_rejects_invalid_action_fields(self, client, auth_headers, action):
        response = client.post(
            "/api/scenes",
            json={"name": "Invalid scene", "actions_json": json.dumps([action])},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_scene_actions"

    def test_create_scene_accepts_empty_action_list(self, client, auth_headers):
        response = client.post(
            "/api/scenes",
            json={"name": "Empty scene", "actions_json": "[]"},
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_create_scene_rejects_nested_non_finite_params_without_side_effects(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        actions_json = (
            '[{"device_type":"light","room_id":"livingroom","action":"on",'
            '"params":{"metadata":{"reading":1e309}}}]'
        )
        published = []
        monkeypatch.setattr(
            scenes_api.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        before_scenes = db.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        response = client.post(
            "/api/scenes",
            json={"name": "Non-finite scene", "actions_json": actions_json},
            headers=auth_headers,
        )

        after_scenes = db.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        after_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_scene_actions"
        assert published == []
        assert after_scenes == before_scenes
        assert after_status == before_status
        assert after_logs == before_logs

    def test_scene_without_room_id_keeps_source_and_executes_in_livingroom(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        actions_json = '[{"device_type":"light","action":"on","params":{}}]'
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        created = client.post(
            "/api/scenes",
            json={"name": "Default room", "actions_json": actions_json},
            headers=auth_headers,
        )
        assert created.status_code == 200

        scene_id = created.json()["id"]
        detail = client.get(f"/api/scenes/{scene_id}", headers=auth_headers)
        executed = client.post(f"/api/scenes/{scene_id}/execute", headers=auth_headers)

        assert detail.status_code == 200
        assert detail.json()["actions_json"] == actions_json
        assert executed.status_code == 200
        assert_command_messages(published, [("home/livingroom/light/command", {"action": "on"})])

    def test_scene_accepts_legacy_device_id_targets(self, client, auth_headers, monkeypatch):
        actions = [
            {
                "device_id": 4,
                "action": "set_brightness",
                "params": {"brightness": 30},
            },
            {
                "device_id": 5,
                "action": "set",
                "params": {"mode": "cool", "temperature": 25},
            },
        ]
        actions_json = json.dumps(actions, separators=(",", ":"))
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        created = client.post(
            "/api/scenes",
            json={"name": "Legacy targets", "actions_json": actions_json},
            headers=auth_headers,
        )
        assert created.status_code == 200

        scene_id = created.json()["id"]
        detail = client.get(f"/api/scenes/{scene_id}", headers=auth_headers)
        executed = client.post(f"/api/scenes/{scene_id}/execute", headers=auth_headers)

        assert detail.status_code == 200
        assert detail.json()["actions_json"] == actions_json
        assert executed.status_code == 200
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "set", "brightness": 30}),
            (
                "home/livingroom/ac/command",
                {"action": "set", "mode": "cool", "temperature": 25},
            ),
        ])

    def test_scene_ignores_user_supplied_internal_mqtt_topic(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        actions_json = json.dumps(
            [
                {
                    "device_type": "light",
                    "room_id": "livingroom",
                    "action": "on",
                    "params": {},
                    "_mqtt_topic": "attacker/override",
                }
            ]
        )
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        created = client.post(
            "/api/scenes",
            json={"name": "Reserved field", "actions_json": actions_json},
            headers=auth_headers,
        )
        assert created.status_code == 200

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert_command_messages(published, [("home/livingroom/light/command", {"action": "on"})])

    def test_update_scene_rejects_invalid_actions(self, client, auth_headers):
        response = client.put(
            "/api/scenes/1",
            json={"actions_json": "{}"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_scene_actions"

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

    def test_execute_scene_rejects_historical_invalid_actions_without_publish(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            scenes_api.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        db.execute("UPDATE scenes SET actions_json = ? WHERE id = 1", ("123",))
        db.commit()

        response = client.post("/api/scenes/1/execute", headers=auth_headers)

        assert response.status_code == 409
        assert response.json()["detail"] == "invalid_scene_actions"
        assert published == []


class TestSceneCommandIntegration:
    def test_resolvable_scene_action_updates_status_and_device_log(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        actions_json = json.dumps(
            [
                {
                    "device_type": "light",
                    "room_id": "livingroom",
                    "action": "on",
                    "params": {"brightness": 72},
                }
            ]
        )
        created = client.post(
            "/api/scenes",
            json={"name": "Command-backed scene", "actions_json": actions_json},
            headers=auth_headers,
        )
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": published[0][1]["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 72},
            },
        )
        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        after_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        assert response.status_code == 200
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "on", "brightness": 72})
        ])
        assert stored["power"] == "on"
        assert stored["brightness"] == 72
        assert after_logs == before_logs + 1

    def test_activity_log_failure_does_not_fail_completed_scene(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        created = client.post(
            "/api/scenes",
            json={
                "name": "Activity log failure",
                "actions_json": json.dumps(
                    [
                        {
                            "device_id": 4,
                            "action": "on",
                            "params": {"brightness": 72},
                        }
                    ]
                ),
            },
            headers=auth_headers,
        )
        assert created.status_code == 200

        def fail_activity_log(**kwargs):
            raise RuntimeError("activity log unavailable")

        monkeypatch.setattr(scenes_api, "write_activity", fail_activity_log)

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["executed"] == 1
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "on", "brightness": 72})
        ])

    def test_unmapped_historical_scene_action_publishes_without_fake_state(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            scenes_api.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: pytest.fail("unmapped target used command service"),
        )
        actions_json = json.dumps(
            [
                {
                    "device_type": "light",
                    "room_id": "garage",
                    "action": "on",
                    "params": {"brightness": 25},
                }
            ]
        )
        created = client.post(
            "/api/scenes",
            json={"name": "Historical garage", "actions_json": actions_json},
            headers=auth_headers,
        )
        before_statuses = db.execute(
            "SELECT id, status_json FROM devices ORDER BY id"
        ).fetchall()
        before_logs = db.execute("SELECT COUNT(*) FROM device_log").fetchone()[0]

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        after_statuses = db.execute(
            "SELECT id, status_json FROM devices ORDER BY id"
        ).fetchall()
        after_logs = db.execute("SELECT COUNT(*) FROM device_log").fetchone()[0]
        assert response.status_code == 200
        assert published == [
            ("home/garage/light/command", {"action": "on", "brightness": 25})
        ]
        assert [tuple(row) for row in after_statuses] == [
            tuple(row) for row in before_statuses
        ]
        assert after_logs == before_logs

    def test_second_scene_dispatch_failure_reports_partial_progress(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        calls = []

        def publish(topic, payload):
            calls.append((topic, json.loads(payload)))
            if len(calls) == 2:
                raise HTTPException(status_code=502, detail="mqtt offline")

        monkeypatch.setattr(device_command_service, "publish_message", publish)
        monkeypatch.setattr(scenes_api.mqtt_client, "publish_message", publish)
        actions_json = json.dumps(
            [
                {"device_id": 4, "action": "on", "params": {"brightness": 31}},
                {"device_id": 5, "action": "on", "params": {}},
            ]
        )
        created = client.post(
            "/api/scenes",
            json={"name": "Partial scene", "actions_json": actions_json},
            headers=auth_headers,
        )

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": calls[0][1]["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 31},
            },
        )
        light_status = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        assert response.status_code == 502
        assert response.json()["detail"] == {
            "code": "scene_partial_failure",
            "executed": 1,
            "failed_index": 1,
        }
        assert light_status["power"] == "on"
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0] == 1
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 5"
        ).fetchone()[0] == 0

    def test_scene_prevalidates_all_actions_before_first_publish(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            scenes_api.mqtt_client,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        db.execute(
            "UPDATE scenes SET actions_json = ? WHERE id = 1",
            (
                json.dumps(
                    [
                        {
                            "device_type": "light",
                            "room_id": "livingroom",
                            "action": "on",
                            "params": {},
                        },
                        {
                            "device_type": "light",
                            "room_id": "bedroom",
                            "action": "destroy",
                            "params": {},
                        },
                    ]
                ),
            ),
        )
        db.commit()

        response = client.post("/api/scenes/1/execute", headers=auth_headers)

        assert response.status_code == 409
        assert response.json()["detail"] == "invalid_scene_actions"
        assert published == []


class TestScenePostDispatchFailures:
    def test_post_dispatch_database_failure_counts_published_action(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        import sqlite3

        created = client.post(
            "/api/scenes",
            json={
                "name": "Post-dispatch failure",
                "actions_json": json.dumps(
                    [
                        {
                            "device_id": 4,
                            "action": "on",
                            "params": {"brightness": 52},
                        }
                    ]
                ),
            },
            headers=auth_headers,
        )
        assert created.status_code == 200

        real_get_db = device_command_service.get_db
        get_db_calls = 0
        published = []

        class FailingDatabaseContext:
            def __enter__(self):
                raise sqlite3.OperationalError("device log unavailable")

            def __exit__(self, exc_type, exc, traceback):
                return False

        def sequenced_get_db():
            nonlocal get_db_calls
            get_db_calls += 1
            if get_db_calls <= 2:
                return real_get_db()
            return FailingDatabaseContext()

        monkeypatch.setattr(device_command_service, "get_db", sequenced_get_db)
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        response = client.post(
            f"/api/scenes/{created.json()['id']}/execute",
            headers=auth_headers,
        )

        assert response.status_code == 502
        assert response.json()["detail"] == {
            "code": "scene_partial_failure",
            "executed": 1,
            "failed_index": 0,
        }
        assert_command_messages(published, [
            ("home/livingroom/light/command", {"action": "on", "brightness": 52})
        ])
