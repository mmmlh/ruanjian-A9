import app.main as main_module


def test_ready_when_database_and_mqtt_are_available(client, monkeypatch):
    monkeypatch.setattr(main_module, "is_mqtt_connected", lambda: True, raising=False)

    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "mqtt": "ok"},
    }
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_not_ready_when_mqtt_is_offline(client, monkeypatch):
    monkeypatch.setattr(main_module, "is_mqtt_connected", lambda: False, raising=False)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "mqtt": "down"},
    }
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_not_ready_when_database_check_fails(client, monkeypatch):
    def fail_get_db():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main_module, "get_db", fail_get_db, raising=False)
    monkeypatch.setattr(main_module, "is_mqtt_connected", lambda: True, raising=False)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "down", "mqtt": "ok"},
    }
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
