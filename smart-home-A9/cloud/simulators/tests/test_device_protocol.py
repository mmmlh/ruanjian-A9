import json
import sys
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from light_controller import LightController
from ac_controller import ACController
from curtain_controller import CurtainController
from door_lock import DoorLock
from humidifier_controller import HumidifierController
from humidity_sensor import HumiditySensor
from pir_sensor import PIRSensor
from temperature_sensor import TemperatureSensor


class FakeClient:
    def __init__(self):
        self.published = []
        self.retained = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, json.loads(payload), qos))
        self.retained.append(retain)


def test_light_announces_hardware_identity_and_capabilities():
    device = LightController(4, "livingroom")
    device.client = FakeClient()

    device.publish_hello()

    topic, payload, qos = device.client.published[-1]
    retain = device.client.retained[-1]
    assert topic == "home/livingroom/light/hello"
    assert qos == 1
    assert retain is True
    assert payload == {
        "hardware_id": "sim-light-004",
        "protocol_version": "1.0",
        "capabilities": {
            "actions": ["on", "off", "set"],
            "params": {
                "brightness": {"min": 0, "max": 100},
                "color": {"values": ["warm", "neutral", "cool"]},
            },
        },
    }


def test_heartbeat_reannounces_hardware_identity_after_backend_restart():
    device = LightController(4, "livingroom")
    device.client = FakeClient()

    device.publish_heartbeat()

    assert [message[0] for message in device.client.published] == [
        "home/livingroom/light/hello",
        "home/livingroom/light/heartbeat",
    ]


def test_light_acknowledges_a_command_with_its_command_id_and_state():
    device = LightController(4, "livingroom")
    device.client = FakeClient()

    device.handle_command(
        {
            "command_id": "cmd-light-1",
            "action": "on",
            "brightness": 80,
            "color": "warm",
        }
    )

    topic, payload, qos = device.client.published[-1]
    assert topic == "home/livingroom/light/ack"
    assert qos == 1
    assert payload == {
        "command_id": "cmd-light-1",
        "success": True,
        "state": {"power": "on", "brightness": 80, "color": "warm"},
    }


def test_light_rejects_invalid_color_without_changing_confirmed_state():
    device = LightController(4, "livingroom")
    device.client = FakeClient()

    device.handle_command(
        {
            "command_id": "cmd-light-invalid",
            "action": "on",
            "brightness": 80,
            "color": "ultraviolet",
        }
    )

    _, payload, _ = device.client.published[-1]
    assert payload == {
        "command_id": "cmd-light-invalid",
        "success": False,
        "error_code": "INVALID_PARAMS",
        "state": {"power": "off", "brightness": 0, "color": "warm"},
    }


def test_all_simulator_types_declare_their_real_capabilities():
    devices = [
        (TemperatureSensor(1, "livingroom"), ["set_config"]),
        (HumiditySensor(2, "livingroom"), ["set_config"]),
        (PIRSensor(3, "livingroom"), ["set_config"]),
        (ACController(5, "livingroom"), ["on", "off", "set"]),
        (DoorLock(6, "livingroom"), ["unlock", "lock"]),
        (CurtainController(15, "livingroom"), ["open", "close", "set"]),
        (HumidifierController(17, "bedroom"), ["on", "off", "set"]),
    ]

    for device, actions in devices:
        assert device.capabilities()["actions"] == actions


def test_sensor_configuration_is_applied_and_acknowledged():
    device = TemperatureSensor(1, "livingroom")
    device.client = FakeClient()

    device.handle_command(
        {
            "command_id": "cmd-temperature-config",
            "action": "set_config",
            "sample_interval_seconds": 12,
            "calibration": 1.5,
            "reporting_enabled": False,
        }
    )

    topic, payload, _ = device.client.published[-1]
    assert topic == "home/livingroom/temperature_sensor/ack"
    assert payload == {
        "command_id": "cmd-temperature-config",
        "success": True,
        "state": {
            "sample_interval_seconds": 12,
            "calibration": 1.5,
            "reporting_enabled": False,
        },
    }


def test_ac_curtain_and_humidifier_acknowledge_their_extended_states():
    devices_and_commands = [
        (
            ACController(5, "livingroom"),
            {"command_id": "cmd-ac", "action": "set", "power": "on", "mode": "heat", "temp": 23, "fan": "high", "swing": "on"},
            "home/livingroom/ac/ack",
            {"power": "on", "mode": "heat", "temp": 23, "fan": "high", "swing": "on"},
        ),
        (
            CurtainController(15, "livingroom"),
            {"command_id": "cmd-curtain", "action": "set", "position": 45},
            "home/livingroom/curtain/ack",
            {"position": 45, "motion": "stopped"},
        ),
        (
            HumidifierController(17, "bedroom"),
            {"command_id": "cmd-humidifier", "action": "set", "power": "on", "level": 3, "target_humidity": 65},
            "home/bedroom/humidifier/ack",
            {"power": "on", "level": 3, "target_humidity": 65, "water_level": 100},
        ),
    ]

    for device, command, topic, expected_state in devices_and_commands:
        device.client = FakeClient()
        device.handle_command(command)
        actual_topic, payload, _ = device.client.published[-1]
        assert actual_topic == topic
        assert payload == {"command_id": command["command_id"], "success": True, "state": expected_state}


def test_door_lock_rejects_an_invalid_auth_code_with_an_explicit_ack():
    device = DoorLock(6, "livingroom")
    device.client = FakeClient()

    device.handle_command({"command_id": "cmd-door", "action": "unlock", "auth_code": "bad"})

    _, payload, _ = device.client.published[-1]
    assert payload == {
        "command_id": "cmd-door",
        "success": False,
        "error_code": "AUTH_FAILED",
        "state": {"locked": True},
    }


def test_all_commandable_simulators_tag_command_status_with_command_id():
    devices_and_commands = [
        (TemperatureSensor(1, "livingroom"), {"command_id": "temperature", "action": "set_config"}),
        (HumiditySensor(2, "livingroom"), {"command_id": "humidity", "action": "set_config"}),
        (PIRSensor(3, "livingroom"), {"command_id": "pir", "action": "set_config"}),
        (LightController(4, "livingroom"), {"command_id": "light", "action": "on"}),
        (ACController(5, "livingroom"), {"command_id": "ac", "action": "on"}),
        (DoorLock(6, "livingroom"), {"command_id": "door", "action": "lock"}),
        (CurtainController(15, "livingroom"), {"command_id": "curtain", "action": "open"}),
        (HumidifierController(17, "bedroom"), {"command_id": "humidifier", "action": "on"}),
    ]

    for device, command in devices_and_commands:
        device.client = FakeClient()
        device.handle_command(command)
        status_topic, status, _ = device.client.published[-2]
        assert status_topic.endswith("/status")
        assert status["command_id"] == command["command_id"]
