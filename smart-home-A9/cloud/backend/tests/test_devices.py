"""
Device management API tests.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import app.services.device_command as device_command_service
from app.main import on_mqtt_message


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

    def test_service_call_rejects_offline_device_with_structured_error(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("2000-01-01 00:00:00",))
        db.commit()

        response = client.post(
            "/api/services",
            json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
            headers=auth_headers,
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["success"] is False
        assert payload["detail"] == "device_offline"
        assert payload["message"] == "device_offline"
        assert payload["entity_id"] == "light.device_4"
        assert payload["action"] == "on"
        assert payload["changed_states"] == []
        assert payload["service_response"] == {}
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
                    "online": True,
                    "status_summary": "forged",
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        stored = json.loads(db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"])
        assert stored["brightness"] == 42
        assert "online" not in stored
        assert "status_summary" not in stored
