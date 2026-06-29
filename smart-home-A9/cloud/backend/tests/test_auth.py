"""
认证 API 测试：注册、登录、个人信息
"""
import pytest


class TestAuth:
    """认证流程测试"""

    def test_root_health(self, client):
        """健康检查"""
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "智能家居设备控制系统"

    def test_health_api(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

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
