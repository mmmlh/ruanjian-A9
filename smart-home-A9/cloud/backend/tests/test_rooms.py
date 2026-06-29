"""
房间管理 API 测试
"""
import pytest


class TestRooms:
    """房间 CRUD 测试"""

    def test_list_rooms(self, client, auth_headers):
        r = client.get("/api/rooms", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 2  # 种子数据有客厅 + 卧室
        names = [room["name"] for room in data]
        assert "客厅" in names
        assert "卧室" in names

    def test_get_room_detail(self, client, auth_headers):
        r = client.get("/api/rooms/1", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "客厅"
        assert data["floor"] == 1
        assert "devices" in data  # 房间详情包含设备列表

    def test_get_room_not_found(self, client, auth_headers):
        r = client.get("/api/rooms/999", headers=auth_headers)
        assert r.status_code == 404

    def test_create_room(self, client, auth_headers):
        r = client.post("/api/rooms", json={
            "name": "厨房",
            "floor": 1,
            "description": "家庭厨房区域",
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "厨房"
        assert "id" in data

    def test_update_room(self, client, auth_headers):
        r = client.put("/api/rooms/1", json={
            "name": "大客厅",
            "description": "更新后的客厅",
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "大客厅" in data["name"] or data.get("message")

    def test_delete_room_with_devices_fails(self, client, auth_headers):
        """有设备的房间不能删除"""
        r = client.delete("/api/rooms/1", headers=auth_headers)
        assert r.status_code == 400

    def test_delete_empty_room(self, client, auth_headers):
        """空房间可以删除"""
        # 先创建一个空房间
        cr = client.post("/api/rooms", json={"name": "临时房间"}, headers=auth_headers)
        room_id = cr.json()["id"]
        r = client.delete(f"/api/rooms/{room_id}", headers=auth_headers)
        assert r.status_code == 200

    def test_unauthorized_access(self, client):
        """未认证不能访问"""
        r = client.get("/api/rooms")
        assert r.status_code == 401
