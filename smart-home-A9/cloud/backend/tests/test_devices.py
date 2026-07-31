"""
Device management API tests.
"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import pytest

import app.main as main_module
import app.services.device_command as device_command_service
from app.main import on_mqtt_message
from app.services.rule_engine import rule_engine


class TestDevices:
    def test_init_db_migrates_legacy_devices_table_to_add_updated_at(self):
        from app.database.connection import DB_PATH, init_db

        db_file = Path(DB_PATH)
        wal_file = Path(f"{DB_PATH}-wal")
        shm_file = Path(f"{DB_PATH}-shm")
        for path in (db_file, wal_file, shm_file):
            if path.exists():
                path.unlink()

        conn = sqlite3.connect(DB_PATH)
        conn.executescript(
            """
            CREATE TABLE devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                brand TEXT,
                mqtt_topic TEXT NOT NULL,
                status_json TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        conn.close()

        init_db()

        migrated = sqlite3.connect(DB_PATH)
        try:
            columns = [row[1] for row in migrated.execute("PRAGMA table_info(devices)").fetchall()]
        finally:
            migrated.close()

        assert "updated_at" in columns

    def test_list_all_devices(self, client, auth_headers):
        response = client.get("/api/devices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data
        assert all("id" in device for device in data)
        assert all("room_id" in device for device in data)

    def test_list_devices_include_presentation_fields(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("2000-01-01 00:00:00",))
        db.commit()

        response = client.get("/api/devices", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        device = next(item for item in data if item["id"] == 4)
        assert device["online"] is False
        assert isinstance(device["status_summary"], str)
        assert device["status_summary"].strip()
        parsed = datetime.fromisoformat(device["last_seen_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_device_detail_returns_null_last_seen_for_missing_timestamp(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = NULL, created_at = NULL WHERE id = 4")
        db.commit()

        response = client.get("/api/devices/4", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["online"] is False
        assert data["last_seen_at"] is None

    def test_device_detail_returns_null_last_seen_for_invalid_timestamp(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("not-a-date",))
        db.commit()

        response = client.get("/api/devices/4", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["online"] is False
        assert data["last_seen_at"] is None

    def test_filter_by_room(self, client, auth_headers):
        response = client.get("/api/devices?room_id=1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data
        for device in data:
            assert device["room_id"] == 1

    def test_filter_by_type(self, client, auth_headers):
        response = client.get("/api/devices?type=temperature_sensor", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data
        for device in data:
            assert device["type"] == "temperature_sensor"

    def test_get_device_detail(self, client, auth_headers):
        response = client.get("/api/devices/4", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "light"
        assert data["name"] == "客厅主灯"
        assert "status_json" in data
        assert "online" in data
        assert data["status_summary"]
        assert "last_seen_at" in data

    def test_device_detail_tolerates_invalid_status_json(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 4", ("{bad",))
        db.commit()

        response = client.get("/api/devices/4", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == {}
        assert data["status_summary"] == "已关闭"

    def test_device_detail_tolerates_non_mapping_status_json(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 4", ('["unexpected"]',))
        db.commit()

        response = client.get("/api/devices/4", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == {}
        assert data["status_summary"] == "已关闭"

    def test_get_device_not_found(self, client, auth_headers):
        response = client.get("/api/devices/999", headers=auth_headers)
        assert response.status_code == 404

    def test_send_command_to_light(self, client, auth_headers):
        response = client.post(
            "/api/devices/4/command",
            json={"action": "on", "params": {"brightness": 80, "color": "warm"}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_command_to_ac(self, client, auth_headers):
        response = client.post(
            "/api/devices/5/command",
            json={"action": "set", "params": {"power": "on", "mode": "cool", "temp": 24}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_command_to_door_lock(self, client, auth_headers):
        response = client.post(
            "/api/devices/6/command",
            json={"action": "unlock", "params": {"auth_code": "demo-auth-code"}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_send_command_device_not_found(self, client, auth_headers):
        response = client.post("/api/devices/999/command", json={"action": "on"}, headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("device_id", "command", "expected_detail"),
        [
            (4, {"action": "destroy", "params": {}}, "unsupported_device_action"),
            (4, {"action": "set", "params": {"brightness": 101}}, "invalid_command_params"),
            (5, {"action": "set", "params": {"temp": 31}}, "invalid_command_params"),
            (15, {"action": "set", "params": {"position": "bad"}}, "invalid_command_params"),
            (6, {"action": "unlock", "params": {}}, "invalid_command_params"),
            (6, {"action": "unlock", "params": {"auth_code": ""}}, "invalid_command_params"),
            (6, {"action": "unlock", "params": {"auth_code": 123}}, "invalid_command_params"),
            (6, {"action": "open", "params": {}}, "invalid_command_params"),
            (6, {"action": "open", "params": {"auth_code": ""}}, "invalid_command_params"),
            (6, {"action": "open", "params": {"auth_code": 123}}, "invalid_command_params"),
            (4, {"action": "on", "params": {"power": "off"}}, "invalid_command_params"),
            (4, {"action": "off", "params": {"power": "on"}}, "invalid_command_params"),
        ],
        ids=[
            "unsupported-action",
            "brightness-too-high",
            "temperature-too-high",
            "position-not-numeric",
            "unlock-missing-auth",
            "unlock-empty-auth",
            "unlock-non-string-auth",
            "open-missing-auth",
            "open-empty-auth",
            "open-non-string-auth",
            "on-with-power-off",
            "off-with-power-on",
        ],
    )
    def test_invalid_command_has_no_side_effects(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
        device_id,
        command,
        expected_detail,
    ):
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = ?", (device_id,)
        ).fetchone()[0]

        response = client.post(
            f"/api/devices/{device_id}/command",
            json=command,
            headers=auth_headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        after_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = ?", (device_id,)
        ).fetchone()[0]
        assert response.status_code == 400
        assert response.json()["detail"] == expected_detail
        assert published == []
        assert after_logs == before_logs
        assert after_status == before_status

    def test_command_rejects_nested_non_finite_params_without_side_effects(
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
            lambda topic, payload: published.append((topic, payload)),
        )
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        headers = {**auth_headers, "Content-Type": "application/json"}

        response = client.post(
            "/api/devices/4/command",
            content='{"action":"set","params":{"metadata":{"reading":1e309}}}',
            headers=headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        after_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_command_params"
        assert published == []
        assert after_logs == before_logs
        assert after_status == before_status

    def test_turning_off_light_resets_brightness(self, client, auth_headers, db):
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            ('{"power":"on","brightness":80}',),
        )
        db.commit()

        response = client.post(
            "/api/devices/4/command",
            json={"action": "off", "params": {"brightness": 60}},
            headers=auth_headers,
        )

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
        )
        assert response.status_code == 200
        assert stored["power"] == "off"
        assert stored["brightness"] == 0

    @pytest.mark.parametrize(
        ("device_id", "action", "params", "canonical_action"),
        [
            (4, "turn_on", {}, "on"),
            (4, "turn_off", {}, "off"),
            (4, "set_brightness", {"brightness": 75}, "set"),
            (6, "open", {"auth_code": "alias-auth-code"}, "unlock"),
            (6, "close", {}, "lock"),
        ],
    )
    def test_compatible_command_aliases_publish_canonical_actions(
        self,
        client,
        auth_headers,
        monkeypatch,
        device_id,
        action,
        params,
        canonical_action,
    ):
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        response = client.post(
            f"/api/devices/{device_id}/command",
            json={"action": action, "params": params},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["payload"]["action"] == canonical_action
        assert published[0][1]["action"] == canonical_action
        for name, value in params.items():
            assert response.json()["payload"][name] == value
            assert published[0][1][name] == value

    @pytest.mark.parametrize(
        ("entity_id", "state"),
        [
            ("curtain.device_15", "bad"),
            ("temperature_sensor.device_1", "bad"),
            ("temperature_sensor.device_1", "nan"),
            ("temperature_sensor.device_1", "inf"),
            ("humidity_sensor.device_2", "bad"),
        ],
    )
    def test_state_write_rejects_invalid_numeric_state_without_mutation(
        self,
        client,
        auth_headers,
        db,
        entity_id,
        state,
    ):
        device_id = int(entity_id.rsplit("_", 1)[1])
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]

        response = client.post(
            f"/api/states/{entity_id}",
            json={"state": state},
            headers=auth_headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_state_value"
        assert after_status == before_status

    @pytest.mark.parametrize(
        ("entity_id", "attributes"),
        [
            ("curtain.device_15", {"position": 101}),
            ("curtain.device_15", {"position": -1}),
            ("curtain.device_15", {"position": "bad"}),
            ("light.device_4", {"brightness": 101}),
            ("light.device_4", {"brightness": -1}),
            ("light.device_4", {"brightness": True}),
            ("ac.device_5", {"temp": 31}),
            ("ac.device_5", {"temp": 15}),
            ("humidifier.device_17", {"level": 4}),
            ("humidifier.device_17", {"level": 0}),
            ("humidifier.device_17", {"target_humidity": 81}),
            ("humidifier.device_17", {"target_humidity": 29}),
            ("temperature_sensor.device_1", {"value": "bad"}),
            ("humidity_sensor.device_2", {"value": False}),
        ],
    )
    def test_state_attributes_reject_invalid_numeric_values_without_mutation(
        self,
        client,
        auth_headers,
        db,
        entity_id,
        attributes,
    ):
        device_id = int(entity_id.rsplit("_", 1)[1])
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]

        response = client.post(
            f"/api/states/{entity_id}",
            json={"attributes": attributes},
            headers=auth_headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_state_value"
        assert after_status == before_status

    @pytest.mark.parametrize(
        "entity_id",
        ["temperature_sensor.device_1", "humidity_sensor.device_2"],
    )
    def test_state_attributes_reject_non_finite_sensor_values_without_mutation(
        self,
        client,
        auth_headers,
        db,
        entity_id,
    ):
        device_id = int(entity_id.rsplit("_", 1)[1])
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        headers = {**auth_headers, "Content-Type": "application/json"}

        response = client.post(
            f"/api/states/{entity_id}",
            content='{"attributes":{"value":1e309}}',
            headers=headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = ?", (device_id,)
        ).fetchone()["status_json"]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_state_value"
        assert after_status == before_status

    def test_state_attributes_reject_nested_non_finite_business_value_without_mutation(
        self,
        client,
        auth_headers,
        db,
    ):
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        headers = {**auth_headers, "Content-Type": "application/json"}

        response = client.post(
            "/api/states/light.device_4",
            content='{"attributes":{"business_data":{"reading":1e309}}}',
            headers=headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_state_value"
        assert after_status == before_status

    @pytest.mark.parametrize(
        ("entity_id", "attribute", "value"),
        [
            ("curtain.device_15", "position", 0),
            ("curtain.device_15", "position", 100),
            ("light.device_4", "brightness", 0),
            ("light.device_4", "brightness", 100),
            ("ac.device_5", "temp", 16),
            ("ac.device_5", "temp", 30),
            ("humidifier.device_17", "level", 1),
            ("humidifier.device_17", "level", 3),
            ("humidifier.device_17", "target_humidity", 30),
            ("humidifier.device_17", "target_humidity", 80),
            ("temperature_sensor.device_1", "value", -12.5),
            ("humidity_sensor.device_2", "value", 55.5),
        ],
    )
    def test_state_attributes_accept_numeric_boundaries(
        self,
        client,
        auth_headers,
        db,
        entity_id,
        attribute,
        value,
    ):
        device_id = int(entity_id.rsplit("_", 1)[1])

        response = client.post(
            f"/api/states/{entity_id}",
            json={"attributes": {attribute: value}},
            headers=auth_headers,
        )

        stored = json.loads(
            db.execute(
                "SELECT status_json FROM devices WHERE id = ?", (device_id,)
            ).fetchone()["status_json"]
        )
        assert response.status_code == 200
        assert stored[attribute] == value

    @pytest.mark.parametrize("decrypted_payload", ["[]", "123", "null"])
    def test_decrypted_command_requires_object_without_side_effects(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
        decrypted_payload,
    ):
        from app.services.security import aes_encrypt, decode_token

        token = auth_headers["Authorization"].split(" ", 1)[1]
        aes_key = decode_token(token)["aes_key"]
        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        response = client.post(
            "/api/devices/4/command",
            json={
                "action": "on",
                "params": {"encrypted": aes_encrypt(decrypted_payload, aes_key)},
            },
            headers=auth_headers,
        )

        after_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        after_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        assert response.status_code == 400
        assert published == []
        assert after_status == before_status
        assert after_logs == before_logs

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_state_endpoint_rejects_entity_type_mismatch(self, client, auth_headers, method):
        if method == "get":
            response = client.get("/api/states/door_lock.device_4", headers=auth_headers)
        else:
            response = client.post(
                "/api/states/door_lock.device_4",
                json={"state": "locked"},
                headers=auth_headers,
            )

        assert response.status_code == 404

    def test_create_device_rejects_duplicate_mqtt_topic(self, client, auth_headers, db):
        topic = "home/livingroom/light"
        before_count = db.execute(
            "SELECT COUNT(*) FROM devices WHERE mqtt_topic = ?", (topic,)
        ).fetchone()[0]

        response = client.post(
            "/api/devices",
            json={
                "room_id": 1,
                "type": "light",
                "name": "Duplicate light",
                "mqtt_topic": topic,
            },
            headers=auth_headers,
        )

        after_count = db.execute(
            "SELECT COUNT(*) FROM devices WHERE mqtt_topic = ?", (topic,)
        ).fetchone()[0]
        assert response.status_code == 409
        assert response.json()["detail"] == "mqtt_topic_already_exists"
        assert before_count == 1
        assert after_count == before_count

    def test_init_db_rejects_existing_duplicate_mqtt_topics(self, client, db):
        from app.database.connection import init_db

        topic = "home/livingroom/light"
        db.execute("DROP INDEX IF EXISTS ux_devices_mqtt_topic")
        db.execute(
            "INSERT INTO devices (room_id, type, name, mqtt_topic) VALUES (?, ?, ?, ?)",
            (1, "light", "Duplicate legacy light", topic),
        )
        db.commit()

        with pytest.raises(RuntimeError, match=topic):
            init_db()

        count = db.execute(
            "SELECT COUNT(*) FROM devices WHERE mqtt_topic = ?", (topic,)
        ).fetchone()[0]
        assert count == 2

    def test_delete_device_with_history_preserves_device_and_log(self, client, auth_headers, db):
        db.execute(
            "INSERT INTO device_log (device_id, action, detail, user_id) VALUES (?, ?, ?, ?)",
            (4, "on", "{}", 1),
        )
        db.commit()

        response = client.delete("/api/devices/4", headers=auth_headers)

        assert response.status_code == 409
        assert response.json()["detail"] == "device_has_history"
        assert db.execute("SELECT COUNT(*) FROM devices WHERE id = 4").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM device_log WHERE device_id = 4").fetchone()[0] == 1

    def test_service_call_returns_changed_state_list_and_ui_message(self, client, auth_headers):
        response = client.post(
            "/api/services",
            json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["message"] == "已下发“on”指令"
        assert payload["entity_id"] == "light.device_4"
        assert payload["action"] == "on"
        assert isinstance(payload["changed_states"], list)
        assert payload["changed_states"]
        assert payload["changed_states"][0]["entity_id"] == "light.device_4"
        assert payload["service_response"]["light.device_4"]["action"] == "on"
        assert payload["service_response"]["light.device_4"]["payload"]["action"] == "on"
        assert payload["service_response"]["light.device_4"]["payload"]["brightness"] == 75
        assert isinstance(payload["executed_at"], str)
        assert payload["executed_at"].strip()
        assert "T" in payload["executed_at"]

    def test_bind_device_response_contains_room_name_and_status_summary(self, client, auth_headers, db, monkeypatch):
        from app.api import discovery as discovery_api

        monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])
        candidate = client.post("/api/discovery", headers=auth_headers).json()["discovered"][0]

        response = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1, "name": "Guest Lamp"},
            headers=auth_headers,
        )

        try:
            assert response.status_code == 200
            payload = response.json()
            assert isinstance(payload["device"]["room_name"], str)
            assert payload["device"]["room_name"].strip()
            assert payload["device"]["status_summary"] == "已关闭"
            assert payload["message"] == f"设备“Guest Lamp”已绑定到“{payload['device']['room_name']}”"
            assert "T" in payload["device"]["last_seen_at"]
            assert payload["device"]["last_seen_at"].endswith("+00:00")
            parsed = datetime.fromisoformat(payload["device"]["last_seen_at"].replace("Z", "+00:00"))
            assert parsed.tzinfo is not None
        finally:
            db.execute("DELETE FROM devices WHERE mqtt_topic = ?", (candidate["mqtt_topic"],))
            db.commit()

    def test_service_call_rejects_entity_type_mismatch(self, client, auth_headers):
        response = client.post(
            "/api/services",
            json={"entity_id": "door_lock.device_4", "action": "lock"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "entity_id_not_found"

    def test_service_call_does_not_mutate_state_when_publish_fails(self, client, auth_headers, db, monkeypatch):
        before_status = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
        before_logs = db.execute("SELECT COUNT(*) FROM device_log WHERE device_id = 4").fetchone()[0]

        def fail_publish(topic: str, payload: str):
            raise RuntimeError("mqtt offline")

        monkeypatch.setattr(device_command_service, "publish_message", fail_publish)

        response = client.post(
            "/api/services",
            json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
            headers=auth_headers,
        )

        after_status = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
        after_logs = db.execute("SELECT COUNT(*) FROM device_log WHERE device_id = 4").fetchone()[0]

        assert response.status_code == 502
        assert response.json()["detail"] == "command_dispatch_failed"
        assert after_status == before_status
        assert after_logs == before_logs

    def test_service_call_accepts_offline_device(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("2000-01-01 00:00:00",))
        db.commit()

        response = client.post(
            "/api/services",
            json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
            headers=auth_headers,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["entity_id"] == "light.device_4"
        assert payload["action"] == "on"
        assert len(payload["changed_states"]) == 1
        assert payload["service_response"]["light.device_4"]["payload"] == {
            "action": "on",
            "brightness": 75,
        }
        assert isinstance(payload["executed_at"], str)
        assert payload["executed_at"].strip()

    def test_mqtt_response_updates_device_state_from_real_device_feedback(self, client, db):
        before = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
        assert '"brightness":0' in before

        on_mqtt_message(
            "home/livingroom/light/response",
            {
                "success": True,
                "state": {
                    "power": "on",
                    "brightness": 91,
                    "color": "warm",
                    "device_id": "light_004",
                },
            },
        )

        after = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
        assert '"power": "on"' in after
        assert '"brightness": 91' in after
        assert '"device_id": "light_004"' not in after

    def test_mqtt_sensor_updates_sensor_device_state_and_freshness(self, client, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 1", ("2000-01-01 00:00:00",))
        db.commit()

        on_mqtt_message(
            "home/livingroom/temperature_sensor/sensor",
            {"value": 26.4, "unit": "celsius", "device_id": "temp_001", "ts": 1},
        )

        row = db.execute("SELECT status_json, updated_at FROM devices WHERE id = 1").fetchone()
        assert json.loads(row["status_json"]) == {"value": 26.4, "unit": "celsius", "ts": 1}
        assert row["updated_at"] != "2000-01-01 00:00:00"

    def test_state_read_tolerates_bad_numeric_status_values(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 15", ('{"position":"bad"}',))
        db.commit()

        response = client.get("/api/states/curtain.device_15", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "unknown"
        assert data["attributes"]["status_summary"] == "位置未知"

    def test_state_write_ignores_derived_presentation_attributes(self, client, auth_headers, db):
        response = client.post(
            "/api/states/light.device_4",
            json={
                "attributes": {
                    "brightness": 42,
                    "color": "warm",
                    "business_data": {"thresholds": [1, 2.5]},
                    "online": True,
                    "status_summary": "forged",
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        stored = json.loads(db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"])
        assert stored["brightness"] == 42
        assert stored["color"] == "warm"
        assert stored["business_data"] == {"thresholds": [1, 2.5]}
        assert "online" not in stored
        assert "status_summary" not in stored


class TestDeviceStateProjection:
    def test_reload_rules_preloads_device_status_from_sqlite(self, client, db):
        from app.services.device_state_projection import device_state_projection

        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            ('{"power":"on","brightness":37}',),
        )
        db.commit()

        rule_engine.reload_rules()

        assert device_state_projection.get(4) == {"power": "on", "brightness": 37}

    def test_reload_rules_replaces_invalid_device_status_with_empty_state(
        self,
        client,
        db,
        caplog,
    ):
        from app.services.device_state_projection import device_state_projection

        db.execute("UPDATE devices SET status_json = ? WHERE id = 4", ("{bad",))
        db.execute("UPDATE devices SET status_json = ? WHERE id = 5", ('["bad"]',))
        db.commit()

        rule_engine.reload_rules()

        assert device_state_projection.get(4) == {}
        assert device_state_projection.get(5) == {}
        assert "invalid device status_json" in caplog.text

    def test_device_command_updates_shared_projection(self, client, auth_headers):
        from app.services.device_state_projection import device_state_projection

        response = client.post(
            "/api/devices/4/command",
            json={"action": "on", "params": {"brightness": 63}},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert device_state_projection.get(4)["power"] == "on"
        assert device_state_projection.get(4)["brightness"] == 63

    def test_state_write_updates_shared_projection(self, client, auth_headers):
        from app.services.device_state_projection import device_state_projection

        response = client.post(
            "/api/states/light.device_4",
            json={"state": "on", "attributes": {"brightness": 44}},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert device_state_projection.get(4)["power"] == "on"
        assert device_state_projection.get(4)["brightness"] == 44

    def test_rebuild_holds_lock_until_loader_result_is_installed(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        loader_started = threading.Event()
        release_loader = threading.Event()
        update_finished = threading.Event()

        def loader():
            loader_started.set()
            assert release_loader.wait(timeout=1)
            return {4: {"power": "off"}}

        rebuild_thread = threading.Thread(target=projection.rebuild, args=(loader,))
        rebuild_thread.start()
        assert loader_started.wait(timeout=1)

        def update():
            projection.update(4, {"power": "on"})
            update_finished.set()

        update_thread = threading.Thread(target=update)
        update_thread.start()
        assert not update_finished.wait(timeout=0.05)

        release_loader.set()
        rebuild_thread.join(timeout=1)
        update_thread.join(timeout=1)

        assert not rebuild_thread.is_alive()
        assert not update_thread.is_alive()
        assert projection.get(4) == {"power": "on"}

    def test_get_returns_a_copy(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        original = {"power": "off"}
        projection.update(4, original)

        original["power"] = "on"
        returned = projection.get(4)
        returned["power"] = "on"

        assert projection.get(4) == {"power": "off"}

    def test_internal_encrypted_command_is_rejected_before_side_effects(
        self,
        client,
        db,
        monkeypatch,
    ):
        from fastapi import HTTPException

        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, payload)),
        )
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        with pytest.raises(HTTPException) as exc_info:
            device_command_service.execute_device_command(
                4,
                "on",
                {"encrypted": "opaque"},
                None,
            )

        assert exc_info.value.status_code == 400
        assert published == []
        assert db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"] == before_status
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0] == before_logs

    def test_mqtt_sync_updates_projection_before_rule_evaluation(
        self,
        client,
        monkeypatch,
    ):
        from app.database.connection import get_db
        from app.services.device_state_projection import device_state_projection

        observed = {}

        def observe_rule_input(topic, payload):
            with get_db() as conn:
                stored = conn.execute(
                    "SELECT status_json FROM devices WHERE id = 1"
                ).fetchone()["status_json"]
            observed["stored"] = json.loads(stored)
            observed["projected"] = device_state_projection.get(1)

        monkeypatch.setattr(main_module.rule_engine, "on_sensor_data", observe_rule_input)
        monkeypatch.setattr(main_module, "_main_event_loop", None)

        on_mqtt_message(
            "home/livingroom/temperature_sensor/sensor",
            {"value": 29.5, "unit": "celsius", "ts": 7},
        )

        expected = {"value": 29.5, "unit": "celsius", "ts": 7}
        assert observed == {"stored": expected, "projected": expected}

    def test_non_mapping_mqtt_payload_stops_before_business_processing(
        self,
        client,
        monkeypatch,
        caplog,
    ):
        calls = []

        class RunningLoop:
            @staticmethod
            def is_running():
                return True

        monkeypatch.setattr(
            main_module.rule_engine,
            "on_sensor_data",
            lambda topic, payload: calls.append("rule"),
        )
        monkeypatch.setattr(
            main_module,
            "_persist_sensor_data",
            lambda topic, payload: calls.append("persist"),
        )
        monkeypatch.setattr(
            main_module,
            "_sync_device_status",
            lambda topic, payload: calls.append("sync"),
        )
        monkeypatch.setattr(
            main_module,
            "broadcast_ws",
            lambda message: calls.append("broadcast"),
        )
        monkeypatch.setattr(main_module, "_main_event_loop", RunningLoop())
        monkeypatch.setattr(
            main_module.asyncio,
            "run_coroutine_threadsafe",
            lambda coroutine, loop: calls.append("websocket"),
        )

        on_mqtt_message("home/livingroom/light/status", ["invalid"])

        assert calls == []
        assert "non-mapping MQTT payload" in caplog.text
