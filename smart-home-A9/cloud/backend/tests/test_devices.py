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
        db.execute(
            "UPDATE devices SET last_seen_at = ?, connection_state = 'offline' WHERE id = 4",
            ("2000-01-01 00:00:00",),
        )
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
        db.execute("UPDATE devices SET last_seen_at = NULL WHERE id = 4")
        db.commit()

        response = client.get("/api/devices/4", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["online"] is False
        assert data["last_seen_at"] is None

    def test_device_detail_returns_null_last_seen_for_invalid_timestamp(self, client, auth_headers, db):
        db.execute("UPDATE devices SET last_seen_at = ? WHERE id = 4", ("not-a-date",))
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
        command_id = response.json()["command_id"]
        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": command_id,
                "success": True,
                "state": {"power": "off", "brightness": 0, "color": "warm"},
            },
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
        command_payload = payload["service_response"]["light.device_4"]["payload"]
        assert command_payload["action"] == "on"
        assert command_payload["brightness"] == 75
        assert command_payload["command_id"]
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
        command_id = response.json()["command_id"]
        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": command_id,
                "success": True,
                "state": {"power": "on", "brightness": 63, "color": "warm"},
            },
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

    def test_update_isolates_nested_state_from_source_mutation(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        source = {
            "details": {
                "history": [
                    {"power": "off"},
                ]
            }
        }

        projection.update(4, source)
        source["details"]["history"][0]["power"] = "on"

        assert projection.get(4)["details"]["history"][0]["power"] == "off"

    def test_get_isolates_nested_state_from_returned_value_mutation(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        projection.update(
            4,
            {"details": {"history": [{"power": "off"}]}},
        )

        returned = projection.get(4)
        returned["details"]["history"][0]["power"] = "on"

        assert projection.get(4)["details"]["history"][0]["power"] == "off"

    def test_rebuild_isolates_nested_state_from_loader_result_mutation(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        loaded = {
            4: {"details": {"history": [{"power": "off"}]}},
        }

        projection.rebuild(lambda: loaded)
        loaded[4]["details"]["history"][0]["power"] = "on"

        assert projection.get(4)["details"]["history"][0]["power"] == "off"

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


class TestProjectionFailureConsistency:
    def test_refresh_holds_lock_and_update_wins_after_loader_finishes(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        loader_started = threading.Event()
        release_loader = threading.Event()
        update_finished = threading.Event()

        def loader():
            loader_started.set()
            assert release_loader.wait(timeout=1)
            return {"details": {"power": "off"}}

        refresh_thread = threading.Thread(
            target=projection.refresh,
            args=(4, loader),
        )
        refresh_thread.start()
        assert loader_started.wait(timeout=1)

        def update():
            projection.update(4, {"details": {"power": "on"}})
            update_finished.set()

        update_thread = threading.Thread(target=update)
        update_thread.start()
        assert not update_finished.wait(timeout=0.05)

        release_loader.set()
        refresh_thread.join(timeout=1)
        update_thread.join(timeout=1)

        assert not refresh_thread.is_alive()
        assert not update_thread.is_alive()
        assert projection.get(4) == {"details": {"power": "on"}}

    def test_refresh_deep_copies_result_and_removes_missing_device(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        loaded = {"details": {"history": [{"power": "off"}]}}

        returned = projection.refresh(4, lambda: loaded)
        loaded["details"]["history"][0]["power"] = "on"
        returned["details"]["history"][0]["power"] = "on"

        assert projection.get(4)["details"]["history"][0]["power"] == "off"
        assert projection.refresh(4, lambda: None) is None
        assert projection.get(4) is None

    def test_multiple_pending_commands_do_not_overwrite_confirmed_state(
        self,
        client,
        db,
        monkeypatch,
    ):
        errors = []
        monkeypatch.setattr(device_command_service, "publish_message", lambda *_: None)
        before = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]

        def run_command(brightness):
            try:
                device_command_service.execute_device_command(
                    4,
                    "set",
                    {"brightness": brightness},
                    {"sub": "1"},
                )
            except Exception as exc:
                errors.append(exc)

        first = threading.Thread(target=run_command, args=(10,), daemon=True)
        second = threading.Thread(target=run_command, args=(90,), daemon=True)
        first.start()
        second.start()
        first.join(timeout=2)
        second.join(timeout=2)

        assert errors == []
        assert not first.is_alive()
        assert not second.is_alive()
        assert db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"] == before
        statuses = [
            row["status"]
            for row in db.execute(
                "SELECT status FROM device_commands WHERE device_id = 4 ORDER BY id"
            )
        ]
        assert statuses == ["pending", "pending"]

    def test_mqtt_status_db_failure_stops_projection_rules_and_websocket(
        self,
        client,
        monkeypatch,
    ):
        import app.database.connection as connection_module
        from app.services.device_state_projection import device_state_projection

        baseline = device_state_projection.get(4)
        calls = []

        class RunningLoop:
            @staticmethod
            def is_running():
                return True

        def fail_get_db():
            raise RuntimeError("status database unavailable")

        monkeypatch.setattr(connection_module, "get_db", fail_get_db)
        monkeypatch.setattr(
            main_module.rule_engine,
            "on_sensor_data",
            lambda *_: calls.append("rule"),
        )
        monkeypatch.setattr(
            main_module,
            "broadcast_ws",
            lambda *_: calls.append("broadcast"),
        )
        monkeypatch.setattr(main_module, "_main_event_loop", RunningLoop())
        monkeypatch.setattr(
            main_module.asyncio,
            "run_coroutine_threadsafe",
            lambda *_: calls.append("websocket"),
        )

        with pytest.raises(RuntimeError, match="status database unavailable"):
            on_mqtt_message(
                "home/livingroom/light/status",
                {"power": "on", "brightness": 88},
            )

        assert calls == []
        assert device_state_projection.get(4) == baseline

    def test_unrelated_mqtt_topic_has_no_status_sync(self, client):
        assert main_module._sync_device_status(
            "home/livingroom/light/telemetry",
            {"power": "on"},
        ) is None

    def test_direct_command_does_not_dispatch_when_command_ledger_persistence_fails(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        real_get_db = device_command_service.get_db
        get_db_calls = 0
        published = []

        class FailingDatabaseContext:
            def __enter__(self):
                raise sqlite3.OperationalError("private sqlite failure")

            def __exit__(self, exc_type, exc, traceback):
                return False

        def sequenced_get_db():
            nonlocal get_db_calls
            get_db_calls += 1
            if get_db_calls == 1:
                return real_get_db()
            return FailingDatabaseContext()

        monkeypatch.setattr(device_command_service, "get_db", sequenced_get_db)
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)
        before_status = db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"]
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        response = client.post(
            "/api/devices/4/command",
            json={"action": "on", "params": {"brightness": 40}},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "command_persistence_failed"
        assert "sqlite" not in response.text.lower()
        assert published == []
        assert db.execute(
            "SELECT status_json FROM devices WHERE id = 4"
        ).fetchone()["status_json"] == before_status
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0] == before_logs

    def test_direct_command_does_not_refresh_projection_before_device_confirmation(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        from app.services.device_state_projection import device_state_projection

        published = []
        monkeypatch.setattr(
            device_command_service,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )
        monkeypatch.setattr(
            device_state_projection,
            "refresh",
            lambda *_: (_ for _ in ()).throw(RuntimeError("refresh failed")),
            raising=False,
        )
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]

        response = client.post(
            "/api/devices/4/command",
            json={"action": "on", "params": {"brightness": 41}},
            headers=auth_headers,
        )

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        assert response.status_code == 200
        assert response.json()["command_status"] == "pending"
        assert len(published) == 1
        assert published[0][0] == "home/livingroom/light/command"
        assert published[0][1]["action"] == "on"
        assert published[0][1]["brightness"] == 41
        assert published[0][1]["command_id"]
        assert stored["power"] == "off"
        assert stored["brightness"] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0] == before_logs + 1

    def test_refresh_failure_invalidates_previous_projection(self):
        from app.services.device_state_projection import DeviceStateProjection

        projection = DeviceStateProjection()
        projection.update(4, {"power": "off"})

        with pytest.raises(RuntimeError, match="loader failed"):
            projection.refresh(
                4,
                lambda: (_ for _ in ()).throw(RuntimeError("loader failed")),
            )

        assert projection.get(4) is None

    def test_state_write_reports_committed_projection_refresh_failure(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        import app.services.device_state_projection as projection_service

        def fail_loader(device_id):
            raise RuntimeError(f"cannot reload {device_id}")

        monkeypatch.setattr(projection_service, "load_device_state", fail_loader)
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)

        response = client.post(
            "/api/states/light.device_4",
            json={"state": "on", "attributes": {"brightness": 77}},
            headers=auth_headers,
        )

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "state_projection_refresh_failed",
            "committed": True,
        }
        assert stored["power"] == "on"
        assert stored["brightness"] == 77
        assert projection_service.device_state_projection.get(4) is None

    def test_pending_command_does_not_overwrite_state_committed_while_publish_is_in_flight(
        self,
        client,
        db,
        monkeypatch,
    ):
        publish_started = threading.Event()
        release_publish = threading.Event()
        errors = []
        before_logs = db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0]
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            (json.dumps({"power": "off", "brightness": 0}),),
        )
        db.commit()

        def publish(*_):
            publish_started.set()
            assert release_publish.wait(timeout=3)

        def run_command():
            try:
                device_command_service.execute_device_command(
                    4,
                    "set",
                    {"brightness": 10},
                    {"sub": "1"},
                )
            except Exception as exc:
                errors.append(exc)

        monkeypatch.setattr(device_command_service, "publish_message", publish)
        command_thread = threading.Thread(target=run_command)
        command_thread.start()
        assert publish_started.wait(timeout=2)

        latest = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        latest["color"] = "red"
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            (json.dumps(latest),),
        )
        db.commit()
        release_publish.set()
        command_thread.join(timeout=10)

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        assert not command_thread.is_alive()
        assert errors == []
        assert stored["brightness"] == 0
        assert stored["color"] == "red"
        assert db.execute(
            "SELECT COUNT(*) FROM device_log WHERE device_id = 4"
        ).fetchone()[0] == before_logs + 1
        assert db.execute(
            "SELECT status FROM device_commands WHERE device_id = 4 ORDER BY id DESC LIMIT 1"
        ).fetchone()["status"] == "pending"

    def test_concurrent_commands_preserve_publish_and_pending_ledger_order(
        self,
        client,
        db,
        monkeypatch,
    ):
        first_published = threading.Event()
        release_first_publish = threading.Event()
        second_published = threading.Event()
        second_finished = threading.Event()
        published = []
        errors = []
        before_log_id = db.execute(
            "SELECT COALESCE(MAX(id), 0) FROM device_log"
        ).fetchone()[0]
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            (json.dumps({"power": "off", "brightness": 0}),),
        )
        db.commit()

        def publish(_topic, raw_payload):
            brightness = json.loads(raw_payload)["brightness"]
            published.append(brightness)
            if brightness == 10:
                first_published.set()
                assert release_first_publish.wait(timeout=3)
            else:
                second_published.set()

        def run_command(brightness, finished=None):
            try:
                device_command_service.execute_device_command(
                    4,
                    "set",
                    {"brightness": brightness},
                    {"sub": "1"},
                )
            except Exception as exc:
                errors.append(exc)
            finally:
                if finished is not None:
                    finished.set()

        monkeypatch.setattr(device_command_service, "publish_message", publish)
        first_thread = threading.Thread(target=run_command, args=(10,))
        second_thread = threading.Thread(
            target=run_command,
            args=(90, second_finished),
        )
        first_thread.start()
        assert first_published.wait(timeout=2)
        second_thread.start()

        if second_published.wait(timeout=0.2):
            assert second_finished.wait(timeout=2)
        release_first_publish.set()
        first_thread.join(timeout=5)
        second_thread.join(timeout=5)

        stored = json.loads(
            db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()[
                "status_json"
            ]
        )
        committed = [
            json.loads(row["detail"])["brightness"]
            for row in db.execute(
                "SELECT detail FROM device_log WHERE id > ? ORDER BY id",
                (before_log_id,),
            ).fetchall()
        ]
        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        assert errors == []
        assert published == [10, 90]
        assert committed == published
        assert stored["brightness"] == 0
        command_statuses = [
            row["status"]
            for row in db.execute(
                "SELECT status FROM device_commands WHERE device_id = 4 ORDER BY id"
            )
        ]
        assert command_statuses == ["pending", "pending"]


class TestDeviceLifecycleProjection:
    def test_bind_success_reloads_device_index_and_projection(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        from app.api import discovery as discovery_api
        from app.services.device_state_projection import device_state_projection

        monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])
        candidate = client.post(
            "/api/discovery",
            headers=auth_headers,
        ).json()["discovered"][0]

        response = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1},
            headers=auth_headers,
        )

        assert response.status_code == 200
        device = response.json()["device"]
        topic_parts = device["mqtt_topic"].split("/")
        assert rule_engine._get_device_id(topic_parts[1], topic_parts[2]) == device["id"]
        assert device_state_projection.get(device["id"]) == device["status"]

        deleted = client.delete(f"/api/devices/{device['id']}", headers=auth_headers)
        assert deleted.status_code == 200

    def test_failed_device_lifecycle_operations_do_not_reload_devices(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        reloads = []
        monkeypatch.setattr(
            rule_engine,
            "reload_devices",
            lambda: reloads.append("reload"),
            raising=False,
        )

        duplicate = client.post(
            "/api/devices",
            json={
                "room_id": 1,
                "type": "light",
                "name": "Duplicate light",
                "mqtt_topic": "home/livingroom/light",
            },
            headers=auth_headers,
        )
        db.execute(
            "INSERT INTO device_log (device_id, action, detail, user_id) VALUES (?, ?, ?, ?)",
            (4, "on", "{}", 1),
        )
        db.commit()
        blocked_delete = client.delete("/api/devices/4", headers=auth_headers)
        missing_bind = client.post(
            "/api/bind_device",
            json={"device_id": "missing-candidate", "room_id": 1},
            headers=auth_headers,
        )

        assert duplicate.status_code == 409
        assert blocked_delete.status_code == 409
        assert missing_bind.status_code == 404
        assert reloads == []

    def test_reload_devices_failure_invalidates_runtime_state(
        self,
        client,
        monkeypatch,
    ):
        from app.services.device_state_projection import device_state_projection

        assert rule_engine._device_id_map
        assert device_state_projection.get(4) is not None
        monkeypatch.setattr(
            device_state_projection,
            "rebuild",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("reload failed")
            ),
        )

        with pytest.raises(RuntimeError, match="reload failed"):
            rule_engine.reload_devices()

        assert rule_engine._device_id_map == {}
        assert device_state_projection.get(4) is None

    def test_create_reports_committed_runtime_reload_failure(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        def fail_reload():
            raise RuntimeError("reload failed")

        monkeypatch.setattr(rule_engine, "reload_devices", fail_reload)
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)
        topic = "home/garage/light"

        response = client.post(
            "/api/devices",
            json={
                "room_id": 1,
                "type": "light",
                "name": "Committed device",
                "mqtt_topic": topic,
            },
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "device_runtime_reload_failed",
            "committed": True,
        }
        assert db.execute(
            "SELECT 1 FROM devices WHERE mqtt_topic = ?", (topic,)
        ).fetchone() is not None

    def test_delete_reports_committed_runtime_reload_failure(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        def fail_reload():
            raise RuntimeError("reload failed")

        monkeypatch.setattr(rule_engine, "reload_devices", fail_reload)
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)

        response = client.delete("/api/devices/4", headers=auth_headers)

        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "device_runtime_reload_failed",
            "committed": True,
        }
        assert db.execute("SELECT 1 FROM devices WHERE id = 4").fetchone() is None

    def test_bind_reports_committed_runtime_reload_failure(
        self,
        client,
        auth_headers,
        db,
        monkeypatch,
    ):
        from app.api import discovery as discovery_api

        monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])
        candidate = client.post(
            "/api/discovery",
            headers=auth_headers,
        ).json()["discovered"][0]

        def fail_reload():
            raise RuntimeError("reload failed")

        monkeypatch.setattr(rule_engine, "reload_devices", fail_reload)
        monkeypatch.setattr(client._transport, "raise_server_exceptions", False)
        response = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "device_runtime_reload_failed",
            "committed": True,
        }
        assert db.execute(
            "SELECT 1 FROM devices WHERE mqtt_topic = ?",
            (candidate["mqtt_topic"],),
        ).fetchone() is not None
