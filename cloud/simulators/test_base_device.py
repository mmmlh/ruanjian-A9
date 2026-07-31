import json
import unittest
from unittest.mock import patch

from base_device import BaseDevice


class FakePublication:
    def __init__(self):
        self.wait_timeout = None

    def wait_for_publish(self, timeout=None):
        self.wait_timeout = timeout


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.connected = False
        self.disconnected = False
        self.loop_stopped = False
        self.published = []
        self.subscriptions = []
        self.will = None

    def will_set(self, topic, payload, qos=0, retain=False):
        self.will = (topic, json.loads(payload), qos, retain)

    def connect(self, host, port, keepalive=60):
        self.connected = True

    def loop_start(self):
        pass

    def loop_stop(self):
        self.loop_stopped = True

    def disconnect(self):
        self.disconnected = True

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def publish(self, topic, payload, qos=0, retain=False):
        publication = FakePublication()
        self.published.append((topic, json.loads(payload), qos, retain, publication))
        return publication


class FakeDevice(BaseDevice):
    def __init__(self):
        super().__init__(4, "livingroom", "light")

    def handle_command(self, payload):
        pass

    def generate_data(self):
        return None


class BaseDeviceAvailabilityTest(unittest.TestCase):
    @patch("base_device.mqtt.Client", FakeClient)
    def test_connect_and_stop_publish_retained_availability(self):
        device = FakeDevice()
        device.running = True
        device.connect_mqtt()
        client = device.client

        self.assertIsNotNone(client)
        self.assertEqual(
            client.will,
            (
                "home/livingroom/light/availability",
                {"online": False, "device_id": "light_004", "ts": client.will[1]["ts"]},
                1,
                True,
            ),
        )

        device._on_connect(client, None, None, 0)
        self.assertTrue(device.connected)
        self.assertEqual(client.subscriptions, ["home/livingroom/light/command"])
        self.assertTrue(client.published[-1][1]["online"])
        self.assertTrue(client.published[-1][3])

        device.stop()
        self.assertFalse(device.connected)
        self.assertFalse(client.published[-1][1]["online"])
        self.assertTrue(client.published[-1][3])
        self.assertEqual(client.published[-1][4].wait_timeout, 2)
        self.assertTrue(client.loop_stopped)
        self.assertTrue(client.disconnected)


if __name__ == "__main__":
    unittest.main()
