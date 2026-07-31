"""Small dependency-free HTTP server for the simulator dashboard."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from device_registry import DEVICE_META, DeviceRegistry, RegistryError

logger = logging.getLogger(__name__)
STATIC_ROOT = Path(__file__).resolve().parent / "web"
DEVICE_ROUTE = re.compile(r"^/api/devices/(\d+)(?:/(command|sensor|start|stop))?$")


class SimulatorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, registry: DeviceRegistry):
        super().__init__(address, handler)
        self.registry = registry


class SimulatorRequestHandler(BaseHTTPRequestHandler):
    server: SimulatorHTTPServer

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            devices = self.server.registry.list_devices()
            self._json(
                200,
                {
                    "status": "ok",
                    "device_count": len(devices),
                    "running_count": sum(1 for item in devices if item["running"]),
                    "connected_count": sum(1 for item in devices if item["connected"]),
                },
            )
            return
        if path == "/api/devices":
            self._json(200, {"devices": self.server.registry.list_devices()})
            return
        if path == "/api/meta":
            devices = self.server.registry.list_devices()
            rooms = sorted({item["room"] for item in devices})
            self._json(200, {"device_types": DEVICE_META, "rooms": rooms})
            return
        self._serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/devices":
                self._json(201, {"device": self.server.registry.add_device(payload)})
                return
            match = DEVICE_ROUTE.fullmatch(path)
            if not match:
                self._json(404, {"error": "Route not found"})
                return
            device_id = int(match.group(1))
            action = match.group(2)
            if action == "command":
                result = self.server.registry.send_command(device_id, payload)
            elif action == "sensor":
                result = self.server.registry.inject_sensor(device_id, payload)
            elif action == "start":
                result = {"device": self.server.registry.set_running(device_id, True)}
            elif action == "stop":
                result = {"device": self.server.registry.set_running(device_id, False)}
            else:
                self._json(405, {"error": "Operation is not supported"})
                return
            self._json(200, result)
        except RegistryError as exc:
            self._json(400, {"error": str(exc)})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "Request body must be valid JSON"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        match = DEVICE_ROUTE.fullmatch(path)
        if not match or match.group(2):
            self._json(404, {"error": "Route not found"})
            return
        try:
            device_id = int(match.group(1))
            self.server.registry.remove_device(device_id)
            self._json(200, {"removed": True, "device_id": device_id})
        except RegistryError as exc:
            self._json(404, {"error": str(exc)})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64 * 1024:
            raise RegistryError("Request body is too large")
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, path: str):
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (STATIC_ROOT / relative).resolve()
        try:
            candidate.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self._json(404, {"error": "File not found"})
            return
        if not candidate.is_file():
            self._json(404, {"error": "File not found"})
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: int, payload):
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args):
        logger.debug("dashboard request: " + fmt, *args)


def create_server(registry: DeviceRegistry, host: str, port: int) -> SimulatorHTTPServer:
    return SimulatorHTTPServer((host, port), SimulatorRequestHandler, registry)
