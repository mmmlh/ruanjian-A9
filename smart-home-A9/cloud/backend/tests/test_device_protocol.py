import json

from app.main import on_mqtt_message


def test_hello_records_real_device_identity_capabilities_and_presence(client, db):
    on_mqtt_message(
        "home/livingroom/light/hello",
        {
            "hardware_id": "sim-light-004",
            "protocol_version": "1.0",
            "capabilities": {
                "actions": ["on", "off", "set"],
                "params": {"brightness": {"min": 0, "max": 100}},
            },
        },
    )

    row = db.execute(
        "SELECT hardware_id, protocol_version, capabilities_json, last_seen_at, connection_state "
        "FROM devices WHERE id = 4"
    ).fetchone()
    assert row["hardware_id"] == "sim-light-004"
    assert row["protocol_version"] == "1.0"
    assert json.loads(row["capabilities_json"])["actions"] == ["on", "off", "set"]
    assert row["last_seen_at"] is not None
    assert row["connection_state"] == "online"


def test_device_is_not_reported_online_until_it_sends_a_real_presence_message(client, auth_headers):
    before = client.get("/api/devices/4", headers=auth_headers).json()
    assert before["online"] is False

    on_mqtt_message(
        "home/livingroom/light/hello",
        {
            "hardware_id": "sim-light-004",
            "protocol_version": "1.0",
            "capabilities": {"actions": ["on", "off", "set"], "params": {}},
        },
    )

    after = client.get("/api/devices/4", headers=auth_headers).json()
    assert after["online"] is True


def test_command_stays_pending_and_preserves_confirmed_state_until_ack(client, auth_headers, db):
    before = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]

    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {"brightness": 80, "color": "warm"}},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["command_status"] == "pending"
    assert body["command_id"]
    assert db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"] == before
    command = db.execute(
        "SELECT device_id, action, params_json, status FROM device_commands WHERE command_id = ?",
        (body["command_id"],),
    ).fetchone()
    assert dict(command) == {
        "device_id": 4,
        "action": "on",
        "params_json": '{"brightness": 80, "color": "warm"}',
        "status": "pending",
    }


def test_command_correlated_status_message_does_not_confirm_state_without_ack(client, auth_headers, db):
    before = db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]
    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {"brightness": 80}},
        headers=auth_headers,
    )
    command_id = response.json()["command_id"]

    on_mqtt_message(
        "home/livingroom/light/status",
        {
            "command_id": command_id,
            "power": "on",
            "brightness": 80,
            "color": "warm",
        },
    )

    assert db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"] == before
    command = db.execute(
        "SELECT status FROM device_commands WHERE command_id = ?", (command_id,)
    ).fetchone()
    assert command["status"] == "pending"


def test_successful_ack_confirms_command_and_updates_state(client, auth_headers, db):
    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {"brightness": 80}},
        headers=auth_headers,
    )
    command_id = response.json()["command_id"]

    on_mqtt_message(
        "home/livingroom/light/ack",
        {
            "command_id": command_id,
            "success": True,
            "state": {"power": "on", "brightness": 80, "color": "warm"},
        },
    )

    command = db.execute(
        "SELECT status, acknowledged_at, error_code FROM device_commands WHERE command_id = ?",
        (command_id,),
    ).fetchone()
    assert command["status"] == "acknowledged"
    assert command["acknowledged_at"] is not None
    assert command["error_code"] is None
    assert json.loads(db.execute("SELECT status_json FROM devices WHERE id = 4").fetchone()["status_json"]) == {
        "power": "on",
        "brightness": 80,
        "color": "warm",
    }


def test_command_status_endpoint_tracks_the_device_acknowledgement(client, auth_headers):
    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {"brightness": 80}},
        headers=auth_headers,
    )
    command_id = response.json()["command_id"]

    pending = client.get(f"/api/devices/commands/{command_id}", headers=auth_headers)

    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    assert pending.json()["device_id"] == 4

    on_mqtt_message(
        "home/livingroom/light/ack",
        {
            "command_id": command_id,
            "success": True,
            "state": {"power": "on", "brightness": 80},
        },
    )

    confirmed = client.get(f"/api/devices/commands/{command_id}", headers=auth_headers)

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "acknowledged"
    assert confirmed.json()["response"]["state"] == {"power": "on", "brightness": 80}


def test_failed_ack_records_error_without_overwriting_confirmed_state(client, auth_headers, db):
    response = client.post(
        "/api/devices/6/command",
        json={"action": "unlock", "params": {"auth_code": "bad-code"}},
        headers=auth_headers,
    )
    command_id = response.json()["command_id"]

    on_mqtt_message(
        "home/livingroom/door_lock/ack",
        {
            "command_id": command_id,
            "success": False,
            "error_code": "AUTH_FAILED",
            "state": {"locked": True},
        },
    )

    command = db.execute(
        "SELECT status, error_code FROM device_commands WHERE command_id = ?",
        (command_id,),
    ).fetchone()
    assert dict(command) == {"status": "failed", "error_code": "AUTH_FAILED"}
    assert json.loads(db.execute("SELECT status_json FROM devices WHERE id = 6").fetchone()["status_json"]) == {
        "locked": True
    }


def test_sensor_configuration_command_is_accepted_as_a_pending_command(client, auth_headers, db):
    response = client.post(
        "/api/devices/1/command",
        json={
            "action": "set_config",
            "params": {"sample_interval_seconds": 12, "calibration": 1.5, "reporting_enabled": False},
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    command = db.execute(
        "SELECT action, status FROM device_commands WHERE command_id = ?",
        (response.json()["command_id"],),
    ).fetchone()
    assert dict(command) == {"action": "set_config", "status": "pending"}


def test_sensor_config_acknowledgement_preserves_the_last_sensor_reading(client, auth_headers, db):
    db.execute(
        "UPDATE devices SET status_json = ? WHERE id = 1",
        ('{"value": 25.0, "unit": "celsius"}',),
    )
    db.commit()
    response = client.post(
        "/api/devices/1/command",
        json={"action": "set_config", "params": {"sample_interval_seconds": 12}},
        headers=auth_headers,
    )

    on_mqtt_message(
        "home/livingroom/temperature_sensor/ack",
        {
            "command_id": response.json()["command_id"],
            "success": True,
            "state": {"sample_interval_seconds": 12, "calibration": 0.0, "reporting_enabled": True},
        },
    )

    state = json.loads(
        db.execute("SELECT status_json FROM devices WHERE id = 1").fetchone()["status_json"]
    )
    assert state == {
        "value": 25.0,
        "unit": "celsius",
        "sample_interval_seconds": 12,
        "calibration": 0.0,
        "reporting_enabled": True,
    }


def test_later_sensor_reading_preserves_confirmed_sensor_configuration(client, auth_headers, db):
    db.execute(
        "UPDATE devices SET status_json = ? WHERE id = 1",
        (
            '{"value": 25.0, "unit": "celsius", "sample_interval_seconds": 12, '
            '"calibration": 0.5, "reporting_enabled": true}',
        ),
    )
    db.commit()

    on_mqtt_message(
        "home/livingroom/temperature_sensor/sensor",
        {"value": 26.0, "unit": "celsius", "ts": 1},
    )

    state = json.loads(
        db.execute("SELECT status_json FROM devices WHERE id = 1").fetchone()["status_json"]
    )
    assert state == {
        "value": 26.0,
        "unit": "celsius",
        "ts": 1,
        "sample_interval_seconds": 12,
        "calibration": 0.5,
        "reporting_enabled": True,
    }


def test_declared_capabilities_reject_an_action_the_device_does_not_support(client, auth_headers):
    on_mqtt_message(
        "home/livingroom/light/hello",
        {
            "hardware_id": "sim-light-004",
            "protocol_version": "1.0",
            "capabilities": {"actions": ["off"], "params": {}},
        },
    )

    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {}},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported_device_action"


def test_declared_capabilities_reject_undeclared_parameters(client, auth_headers):
    on_mqtt_message(
        "home/livingroom/light/hello",
        {
            "hardware_id": "sim-light-004",
            "protocol_version": "1.0",
            "capabilities": {
                "actions": ["on", "off", "set"],
                "params": {"brightness": {"min": 0, "max": 100}},
            },
        },
    )

    response = client.post(
        "/api/devices/4/command",
        json={"action": "on", "params": {"brightness": 80, "unsupported": True}},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_command_params"


def test_declared_capabilities_enforce_the_door_lock_auth_code_length(client, auth_headers):
    on_mqtt_message(
        "home/livingroom/door_lock/hello",
        {
            "hardware_id": "sim-door_lock-006",
            "protocol_version": "1.0",
            "capabilities": {
                "actions": ["unlock", "lock"],
                "params": {"auth_code": {"min_length": 16, "required_for": ["unlock"]}},
            },
        },
    )

    response = client.post(
        "/api/devices/6/command",
        json={"action": "unlock", "params": {"auth_code": "too-short"}},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_command_params"
