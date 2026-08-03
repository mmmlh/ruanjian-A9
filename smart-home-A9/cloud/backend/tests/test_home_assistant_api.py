"""
Home Assistant 风格状态与服务接口测试
"""


from app.main import on_mqtt_message


class TestHomeAssistantApi:
    def test_list_states_includes_extended_seed_entities(self, client, auth_headers):
        response = client.get("/api/states", headers=auth_headers)

        assert response.status_code == 200
        states = response.json()
        entity_ids = {item["entity_id"] for item in states}

        assert "light.device_4" in entity_ids
        assert "curtain.device_15" in entity_ids
        assert "humidifier.device_17" in entity_ids

    def test_call_service_returns_pending_command_until_the_light_acknowledges(self, client, auth_headers):
        response = client.post(
            "/api/services",
            json={
                "entity_id": "light.device_4",
                "action": "on",
                "params": {"brightness": 80, "color": "warm"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["command_status"] == "pending"
        assert body["command_id"]
        assert len(body["changed_states"]) == 1

        changed_state = body["changed_states"][0]
        assert changed_state["entity_id"] == "light.device_4"
        assert changed_state["state"] == "off"

        on_mqtt_message(
            "home/livingroom/light/ack",
            {
                "command_id": body["command_id"],
                "success": True,
                "state": {"power": "on", "brightness": 80, "color": "warm"},
            },
        )

        confirmed = client.get("/api/states/light.device_4", headers=auth_headers).json()
        assert confirmed["state"] == "on"
        assert confirmed["attributes"]["power"] == "on"
        assert confirmed["attributes"]["brightness"] == 80
        assert confirmed["attributes"]["color"] == "warm"

    def test_legacy_device_command_updates_state_view_after_curtain_ack(self, client, auth_headers):
        command_response = client.post(
            "/api/devices/15/command",
            json={
                "action": "set",
                "params": {"position": 65},
            },
            headers=auth_headers,
        )

        assert command_response.status_code == 200
        assert command_response.json()["success"] is True
        assert command_response.json()["command_status"] == "pending"

        on_mqtt_message(
            "home/livingroom/curtain/ack",
            {
                "command_id": command_response.json()["command_id"],
                "success": True,
                "state": {"position": 65, "motion": "stopped"},
            },
        )

        state_response = client.get("/api/states/curtain.device_15", headers=auth_headers)

        assert state_response.status_code == 200
        state_body = state_response.json()
        assert state_body["state"] == "65"
        assert state_body["attributes"]["position"] == 65
