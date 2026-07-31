"""
Dashboard and discovery contract tests for the real-functionality plan.
"""
from datetime import datetime

from app.api import discovery as discovery_api


class TestDashboardContract:
    def _restrict_discovery_to_seeded_rooms(self, monkeypatch):
        monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])

    def test_discovery_returns_candidates_without_creating_real_devices(self, client, auth_headers, db, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)
        before = [
            (row["id"], row["mqtt_topic"], row["status_json"])
            for row in db.execute(
                "SELECT id, mqtt_topic, status_json FROM devices ORDER BY id"
            ).fetchall()
        ]

        response = client.post("/api/discovery", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        after = [
            (row["id"], row["mqtt_topic"], row["status_json"])
            for row in db.execute(
                "SELECT id, mqtt_topic, status_json FROM devices ORDER BY id"
            ).fetchall()
        ]

        assert "discovered" in payload
        assert isinstance(payload["discovered"], list)
        assert payload["mutates_devices"] is False
        assert after == before

    def test_discovery_returns_candidate_status_summary_and_last_seen(self, client, auth_headers, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)

        response = client.post("/api/discovery", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "candidate_catalog"
        assert isinstance(payload["discovered"], list)
        candidate = payload["discovered"][0]
        assert "status" in candidate
        assert "status_summary" in candidate
        assert "last_seen_at" in candidate
        assert candidate["room_hint"] == "客厅"
        assert candidate["name"] == "客厅氛围灯"
        assert candidate["status_summary"] == "已关闭"
        assert isinstance(candidate["status_summary"], str)
        assert candidate["status_summary"].strip()
        parsed = datetime.fromisoformat(candidate["last_seen_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_bind_device_creates_bound_device_from_candidate(self, client, auth_headers, db, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)
        discovery = client.post("/api/discovery", headers=auth_headers)
        assert discovery.status_code == 200
        discovered = discovery.json()["discovered"]
        candidate = discovered[0]
        after_discovery = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

        response = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1, "name": "Guest Lamp"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        payload = response.json()
        after = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

        try:
            assert payload["success"] is True
            assert payload["device"]["room_id"] == 1
            assert payload["device"]["name"] == "Guest Lamp"
            assert payload["message"] == f"设备“Guest Lamp”已绑定到“{payload['device']['room_name']}”"
            assert "T" in payload["device"]["last_seen_at"]
            assert payload["device"]["last_seen_at"].endswith("+00:00")
            parsed = datetime.fromisoformat(payload["device"]["last_seen_at"].replace("Z", "+00:00"))
            assert parsed.tzinfo is not None
            assert after == after_discovery + 1
        finally:
            db.execute("DELETE FROM devices WHERE mqtt_topic = ?", (candidate["mqtt_topic"],))
            db.commit()

    def test_bind_device_rejects_duplicate_binding(self, client, auth_headers, db, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)
        candidate = client.post("/api/discovery", headers=auth_headers).json()["discovered"][0]

        first = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1, "name": "Duplicate Guard"},
            headers=auth_headers,
        )
        assert first.status_code == 200

        second = client.post(
            "/api/bind_device",
            json={"device_id": candidate["id"], "room_id": 1, "name": "Duplicate Guard"},
            headers=auth_headers,
        )

        try:
            assert second.status_code == 409
            assert second.json()["detail"] == "candidate_already_bound"
        finally:
            db.execute("DELETE FROM devices WHERE name = ?", ("Duplicate Guard",))
            db.commit()

    def test_dashboard_summary_devices_include_presentation_fields_and_stats_match_online_flags(
        self,
        client,
        auth_headers,
        db,
    ):
        stale = "2000-01-01 00:00:00"
        fresh = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE devices SET updated_at = ?", (stale,))
        db.execute("UPDATE devices SET updated_at = ? WHERE id IN (4, 5)", (fresh,))
        db.commit()

        response = client.get("/api/dashboard/summary", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        devices = payload["devices"]
        assert devices
        assert all("online" in device for device in devices)
        assert all("status_summary" in device for device in devices)
        assert all("last_seen_at" in device for device in devices)
        assert all(isinstance(device["status_summary"], str) and device["status_summary"].strip() for device in devices)

        online_ids = {device["id"] for device in devices if device["online"]}
        assert online_ids == {4, 5}
        assert payload["stats"]["online_devices"] == len(online_ids)
        assert payload["stats"]["offline_devices"] == len(devices) - len(online_ids)

        parsed = datetime.fromisoformat(devices[0]["last_seen_at"].replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_dashboard_summary_excludes_future_timestamps_from_online_counts(self, client, auth_headers, db):
        stale = "2000-01-01 00:00:00"
        future = "2999-01-01 00:00:00"
        fresh = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE devices SET updated_at = ?", (stale,))
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", (future,))
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 5", (fresh,))
        db.commit()

        response = client.get("/api/dashboard/summary", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        devices = {device["id"]: device for device in payload["devices"]}
        assert devices[4]["online"] is False
        assert devices[5]["online"] is True
        assert payload["stats"]["online_devices"] == 1
        assert payload["stats"]["offline_devices"] == len(devices) - 1

    def test_dashboard_summary_honors_explicit_offline_availability(self, client, auth_headers, db):
        fresh = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", (fresh,))
        db.execute(
            "UPDATE devices SET status_json = ? WHERE id = 4",
            ('{"power":"off","brightness":0,"online":false}',),
        )
        db.commit()

        response = client.get("/api/dashboard/summary", headers=auth_headers)

        assert response.status_code == 200
        devices = {device["id"]: device for device in response.json()["devices"]}
        assert devices[4]["online"] is False

    def test_dashboard_summary_recent_logs_merge_device_and_activity_entries(self, client, auth_headers, db):
        db.execute(
            "INSERT INTO device_log (device_id, action, detail, user_id, timestamp) VALUES (?, ?, ?, ?, ?)",
            (4, "on", '{"brightness": 80}', 1, "2026-07-08 10:00:00"),
        )
        db.execute(
            """
            INSERT INTO activity_log (event_type, title, detail, source, device_id, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("scene", "Sleep Mode", "Scene executed", "scenes.execute", 4, 1, "2026-07-08 10:01:00"),
        )
        db.commit()

        response = client.get("/api/dashboard/summary", headers=auth_headers)

        assert response.status_code == 200
        recent_logs = response.json()["recent_logs"]
        assert recent_logs
        assert recent_logs[0]["source"] == "scenes.execute"
        assert any(item["source"] == "device_log" for item in recent_logs)
        assert any(item["source"] == "scenes.execute" for item in recent_logs)
