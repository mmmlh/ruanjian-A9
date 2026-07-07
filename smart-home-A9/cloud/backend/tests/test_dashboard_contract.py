"""
Dashboard and discovery contract tests for the real-functionality plan.
"""

from app.api import discovery as discovery_api


class TestDashboardContract:
    def _restrict_discovery_to_seeded_rooms(self, monkeypatch):
        monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])

    def test_dashboard_summary_returns_rooms_devices_stats_scenes_and_recent_logs(self, client, auth_headers):
        response = client.get("/api/dashboard/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "rooms" in data
        assert "devices" in data
        assert "stats" in data
        assert "scenes" in data
        assert "recent_logs" in data
        assert data["stats"]["total_devices"] >= len(data["devices"])

    def test_discovery_returns_candidates_without_creating_real_devices(self, client, auth_headers, db, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)
        before = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

        response = client.post("/api/discovery", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        discovered_ids = [item["id"] for item in payload.get("discovered", []) if isinstance(item.get("id"), int)]
        after = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]

        try:
            assert "discovered" in payload
            assert isinstance(payload["discovered"], list)
            assert payload["mutates_devices"] is False
            assert after == before
        finally:
            if discovered_ids:
                placeholders = ",".join("?" for _ in discovered_ids)
                db.execute(f"DELETE FROM devices WHERE id IN ({placeholders})", discovered_ids)
                db.commit()

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
        assert isinstance(candidate["status_summary"], str)
        assert candidate["status_summary"].strip()

    def test_bind_device_creates_bound_device_from_candidate(self, client, auth_headers, db, monkeypatch):
        self._restrict_discovery_to_seeded_rooms(monkeypatch)
        discovery = client.post("/api/discovery", headers=auth_headers)
        assert discovery.status_code == 200
        discovered = discovery.json()["discovered"]
        discovered_ids = [item["id"] for item in discovered if isinstance(item.get("id"), int)]
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
            assert after == after_discovery + 1
        finally:
            if discovered_ids:
                placeholders = ",".join("?" for _ in discovered_ids)
                db.execute(f"DELETE FROM devices WHERE id IN ({placeholders})", discovered_ids)
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
