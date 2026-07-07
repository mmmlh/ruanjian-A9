"""
设备管理 API 测试
"""
from datetime import datetime
import json
import pytest


class TestDevices:
    """设备查询 + 指令下发测试"""

    def test_list_all_devices(self, client, auth_headers):
        r = client.get("/api/devices", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 11  # 6 客厅 + 5 卧室

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

        r = client.get("/api/devices/4", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["online"] is False
        assert data["last_seen_at"] is None

    def test_device_detail_returns_null_last_seen_for_invalid_timestamp(self, client, auth_headers, db):
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("not-a-date",))
        db.commit()

        r = client.get("/api/devices/4", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["online"] is False
        assert data["last_seen_at"] is None

    def test_filter_by_room(self, client, auth_headers):
        r = client.get("/api/devices?room_id=1", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 6  # 客厅 6 个设备
        for d in data:
            assert d["room_id"] == 1

    def test_filter_by_type(self, client, auth_headers):
        r = client.get("/api/devices?type=temperature_sensor", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2  # 客厅 + 卧室各一个
        for d in data:
            assert d["type"] == "temperature_sensor"

    def test_get_device_detail(self, client, auth_headers):
        r = client.get("/api/devices/4", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "light"
        assert data["name"] == "客厅主灯"
        assert "status_json" in data
        assert "online" in data
        assert data["status_summary"]
        assert "last_seen_at" in data

    def test_device_detail_tolerates_invalid_status_json(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 4", ("{bad",))
        db.commit()

        r = client.get("/api/devices/4", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == {}
        assert data["status_summary"] == "Power off"

    def test_device_detail_tolerates_non_mapping_status_json(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 4", ('["unexpected"]',))
        db.commit()

        r = client.get("/api/devices/4", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == {}
        assert data["status_summary"] == "Power off"

    def test_get_device_not_found(self, client, auth_headers):
        r = client.get("/api/devices/999", headers=auth_headers)
        assert r.status_code == 404

    def test_send_command_to_light(self, client, auth_headers):
        r = client.post("/api/devices/4/command", json={
            "action": "on",
            "params": {"brightness": 80, "color": "warm"},
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_send_command_to_ac(self, client, auth_headers):
        r = client.post("/api/devices/5/command", json={
            "action": "set",
            "params": {"power": "on", "mode": "cool", "temp": 24},
        }, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_send_command_to_door_lock(self, client, auth_headers):
        r = client.post("/api/devices/6/command", json={
            "action": "unlock",
            "params": {"auth_code": "demo-auth-code"},
        }, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_send_command_device_not_found(self, client, auth_headers):
        r = client.post("/api/devices/999/command", json={
            "action": "on",
        }, headers=auth_headers)
        assert r.status_code == 404
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
            assert payload["device"]["status_summary"]
            assert "T" in payload["device"]["last_seen_at"]
            assert payload["device"]["last_seen_at"].endswith("+00:00")
            parsed = datetime.fromisoformat(payload["device"]["last_seen_at"].replace("Z", "+00:00"))
            assert parsed.tzinfo is not None
        finally:
            db.execute("DELETE FROM devices WHERE mqtt_topic = ?", (candidate["mqtt_topic"],))
            db.commit()
    def test_state_read_tolerates_bad_numeric_status_values(self, client, auth_headers, db):
        db.execute("UPDATE devices SET status_json = ? WHERE id = 15", ('{"position":"bad"}',))
        db.commit()

        r = client.get("/api/states/curtain.device_15", headers=auth_headers)

        assert r.status_code == 200
        data = r.json()
        assert data["state"] == "unknown"
        assert data["attributes"]["status_summary"] == "Unknown position"

    def test_state_write_ignores_derived_presentation_attributes(self, client, auth_headers, db):
        r = client.post(
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

        assert r.status_code == 200
