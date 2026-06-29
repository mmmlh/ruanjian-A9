"""
设备管理 API 测试
"""
import pytest


class TestDevices:
    """设备查询 + 指令下发测试"""

    def test_list_all_devices(self, client, auth_headers):
        r = client.get("/api/devices", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 11  # 6 客厅 + 5 卧室

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
