"""
认证 API 测试：注册、登录、个人信息
"""
import pytest

from app.services import mqtt_client


class TestAuth:
    """认证流程测试"""

    def test_root_health(self, client):
        """健康检查"""
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "智能家居设备控制系统"

    def test_health_api(self, client, monkeypatch):
        monkeypatch.setattr(mqtt_client, "get_mqtt_status", lambda: {
            "started": True,
            "connected": True,
            "reconnect_count": 0,
            "last_connected_at": "2026-07-30T03:00:00+00:00",
            "last_disconnected_at": None,
            "last_error": None,
        })

        r = client.get("/api/health")

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["dependencies"]["database"] == {"status": "ok"}
        assert data["dependencies"]["mqtt"]["status"] == "ok"
        assert data["dependencies"]["mqtt"]["connected"] is True

    def test_health_api_is_unavailable_when_mqtt_is_offline(self, client, monkeypatch):
        monkeypatch.setattr(mqtt_client, "get_mqtt_status", lambda: {
            "started": True,
            "connected": False,
            "reconnect_count": 2,
            "last_connected_at": "2026-07-30T03:00:00+00:00",
            "last_disconnected_at": "2026-07-30T03:05:00+00:00",
            "last_error": "unexpected_disconnect_rc_7",
        })

        r = client.get("/api/health")

        assert r.status_code == 503
        data = r.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"] == {"status": "ok"}
        assert data["dependencies"]["mqtt"]["status"] == "unavailable"
        assert data["dependencies"]["mqtt"]["reconnect_count"] == 2

    def test_health_api_is_unavailable_when_database_check_fails(self, client, monkeypatch):
        def fail_database_check():
            raise RuntimeError("database unavailable")

        monkeypatch.setattr("app.main.get_db", fail_database_check, raising=False)
        monkeypatch.setattr(mqtt_client, "get_mqtt_status", lambda: {
            "started": True,
            "connected": True,
            "reconnect_count": 0,
            "last_connected_at": "2026-07-30T03:00:00+00:00",
            "last_disconnected_at": None,
            "last_error": None,
        })

        r = client.get("/api/health")

        assert r.status_code == 503
        data = r.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"] == {"status": "unavailable"}
        assert data["dependencies"]["mqtt"]["status"] == "ok"

    def test_register_new_user(self, client):
        r = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "pass123",
            "role": "user",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["username"] == "newuser"
        assert "id" in data["user"]
        assert "token" in data

    def test_register_duplicate_fails(self, client):
        """重复注册应该失败"""
        client.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "pass123",
        })
        r = client.post("/api/auth/register", json={
            "username": "dup_user",
            "password": "pass456",
        })
        assert r.status_code == 400

    def test_login_success(self, client):
        """用种子数据 admin/admin123 登录"""
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["username"] == "admin"

    def test_login_wrong_password(self, client):
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/auth/login", json={
            "username": "ghost_user",
            "password": "whatever",
        })
        assert r.status_code == 401

    def test_get_me_authenticated(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "admin"

    def test_get_me_no_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401
