"""
历史数据查询 API 测试
"""
import json
import pytest
from app.database.connection import get_db


class TestSensorData:
    """传感器数据查询测试"""

    def _insert_test_data(self):
        """插入一条测试传感器数据"""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sensor_data (device_id, data_type, value, extra_json) "
                "VALUES (1, 'temperature', 25.5, '{\"unit\":\"celsius\"}')"
            )

    def test_list_sensor_data_empty(self, client, auth_headers):
        """初始无数据"""
        r = client.get("/api/data/sensors", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_list_sensor_data_with_inserted(self, client, auth_headers):
        self._insert_test_data()
        r = client.get("/api/data/sensors", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["data_type"] == "temperature"
        assert data[0]["value"] == 25.5

    def test_filter_by_device(self, client, auth_headers):
        r = client.get("/api/data/sensors?device_id=1", headers=auth_headers)
        assert r.status_code == 200

    def test_filter_by_type(self, client, auth_headers):
        self._insert_test_data()
        r = client.get("/api/data/sensors?data_type=temperature", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for d in data:
            assert d["data_type"] == "temperature"

    def test_limit_param(self, client, auth_headers):
        r = client.get("/api/data/sensors?limit=5", headers=auth_headers)
        assert r.status_code == 200


class TestDeviceLogs:
    """设备操作日志测试"""

    def test_list_logs_empty(self, client, auth_headers):
        r = client.get("/api/data/logs", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_logs_with_data(self, client, auth_headers):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO device_log (device_id, action, detail, user_id) "
                "VALUES (4, 'on', '{\"brightness\":80}', 1)"
            )
        r = client.get("/api/data/logs", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["action"] == "on"
        assert data[0]["event_type"] == "device"
        assert data[0]["title"] == "on"
        assert data[0]["source"] == "device_log"

    def test_logs_endpoint_returns_activity_log_records(self, client, auth_headers):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO activity_log (event_type, title, detail, source, user_id) VALUES (?, ?, ?, ?, ?)",
                ("scene", "Home Mode", "Executed scene", "scenes.execute", 1),
            )

        response = client.get("/api/data/logs", headers=auth_headers)

        assert response.status_code == 200
        items = response.json()
        assert any(item.get("event_type") == "scene" for item in items)
        scene_item = next(item for item in items if item.get("event_type") == "scene")
        assert scene_item["title"] == "Home Mode"
        assert scene_item["source"] == "scenes.execute"

    def test_logs_endpoint_filters_by_event_type(self, client, auth_headers):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO activity_log (event_type, title, detail, source, user_id) VALUES (?, ?, ?, ?, ?)",
                ("scene", "Away Mode", "Executed scene", "scenes.execute", 1),
            )
            conn.execute(
                "INSERT INTO activity_log (event_type, title, detail, source, user_id) VALUES (?, ?, ?, ?, ?)",
                ("rule", "Auto Cool", "Triggered rule", "rules.trigger", 1),
            )

        response = client.get("/api/data/logs?event_type=scene", headers=auth_headers)

        assert response.status_code == 200
        items = response.json()
        assert items
        assert all(item["event_type"] == "scene" for item in items)
