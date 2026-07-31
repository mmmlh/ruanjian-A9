"""Start the MQTT device simulators and their local management dashboard."""

from __future__ import annotations

import logging
import os
import signal
import threading

from device_registry import DEFAULT_DEVICE_SPECS, DEVICE_CLASSES, DeviceRegistry
from simulator_web import create_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
WEB_HOST = os.getenv("SIMULATOR_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("SIMULATOR_WEB_PORT", "8090"))
AUTO_START = os.getenv("SIMULATOR_AUTO_START", "true").lower() in {"1", "true", "yes", "on"}
CONFIG_PATH = os.getenv(
    "SIMULATOR_CONFIG",
    os.path.join(os.path.dirname(__file__), "data", "devices.json"),
)


def create_devices() -> list:
    """Compatibility helper that creates the original default device set."""
    devices = []
    for spec in DEFAULT_DEVICE_SPECS:
        device_class = DEVICE_CLASSES[spec["type"]]
        kwargs = {"mqtt_broker": MQTT_BROKER, "mqtt_port": MQTT_PORT}
        if spec["type"] == "ac":
            kwargs["brand"] = spec.get("brand", "generic")
        devices.append(device_class(spec["id"], spec["room"], **kwargs))
    return devices


def main():
    registry = DeviceRegistry(MQTT_BROKER, MQTT_PORT, CONFIG_PATH)
    server = create_server(registry, WEB_HOST, WEB_PORT)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info("Simulator dashboard listening on http://%s:%s", WEB_HOST, WEB_PORT)

    stop_event = threading.Event()

    def maintain_devices():
        while not stop_event.is_set():
            registry.start_all()
            stop_event.wait(5)

    device_thread = None
    if AUTO_START:
        device_thread = threading.Thread(target=maintain_devices, daemon=True)
        device_thread.start()

    def request_shutdown(signum=None, frame=None):
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    try:
        while not stop_event.wait(1):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping simulator dashboard and devices")
        server.shutdown()
        server.server_close()
        registry.stop_all()
        server_thread.join(timeout=2)
        if device_thread:
            device_thread.join(timeout=2)


if __name__ == "__main__":
    main()
