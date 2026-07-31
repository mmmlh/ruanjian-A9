"""
FastAPI entrypoint for the smart home backend.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    bind_device,
    dashboard,
    data,
    devices,
    discovery,
    login,
    rooms,
    rules,
    scenes,
    services,
    states,
)
from app.config import CORS_ORIGINS, DEBUG, HOST, PORT
from app.database import init_db
from app.services.device_state_projection import device_state_projection
from app.services.mqtt_client import init_mqtt, stop_mqtt, subscribe
from app.services.rule_engine import rule_engine

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ws_clients: list[WebSocket] = []
_main_event_loop: asyncio.AbstractEventLoop | None = None


async def broadcast_ws(message: dict):
    """Broadcast a JSON message to all connected websocket clients."""
    text = json.dumps(message)
    for ws in ws_clients[:]:
        try:
            await ws.send_text(text)
        except Exception:
            ws_clients.remove(ws)


def on_mqtt_message(topic: str, payload):
    """Handle MQTT messages from simulators and devices."""
    if not isinstance(payload, dict):
        logger.warning("ignored non-mapping MQTT payload on topic %s", topic)
        return

    _persist_sensor_data(topic, payload)
    synced = _sync_device_status(topic, payload)
    if synced is not None:
        device_id, status = synced
        device_state_projection.update(device_id, status)

    rule_engine.on_sensor_data(topic, payload)

    msg = {"type": "mqtt", "topic": topic, "payload": payload}
    if _main_event_loop and _main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_ws(msg), _main_event_loop)


def _persist_sensor_data(topic: str, payload):
    """Persist sensor data published on `.../sensor` topics."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return

    parts = topic.split("/")
    if len(parts) < 4 or parts[-1] != "sensor":
        return

    room_id = parts[1]
    device_type = parts[2]
    mqtt_topic = f"home/{room_id}/{device_type}"

    data_type = None
    value = None
    extra = {}

    if device_type == "temperature_sensor":
        data_type = "temperature"
        value = payload.get("value")
        extra = {"unit": payload.get("unit", "celsius"), "ts": payload.get("ts")}
    elif device_type == "humidity_sensor":
        data_type = "humidity"
        value = payload.get("value")
        extra = {"unit": payload.get("unit", "percent"), "ts": payload.get("ts")}
    elif device_type == "pir_sensor":
        data_type = "presence"
        value = 1.0 if payload.get("presence") else 0.0
        extra = {"ts": payload.get("ts")}
    else:
        return

    if value is None:
        return

    try:
        from app.database.connection import get_db

        with get_db() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE mqtt_topic = ?",
                (mqtt_topic,),
            ).fetchone()
            if device:
                conn.execute(
                    "INSERT INTO sensor_data (device_id, data_type, value, extra_json) VALUES (?, ?, ?, ?)",
                    (device["id"], data_type, value, json.dumps(extra)),
                )
    except Exception as exc:
        logger.error("sensor data persistence failed: %s", exc)


def _sync_device_status(topic: str, payload) -> tuple[int, dict] | None:
    """Persist device state from `.../status`, `.../response`, and `.../sensor` topics."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return

    parts = topic.split("/")
    if len(parts) < 4 or parts[-1] not in {"status", "response", "sensor"}:
        return

    room_id = parts[1]
    device_type = parts[2]
    mqtt_topic = f"home/{room_id}/{device_type}"

    if parts[-1] == "response":
        response_state = payload.get("state") if isinstance(payload, dict) else None
        if not isinstance(response_state, dict):
            return
        payload = response_state

    status = {
        key: value
        for key, value in payload.items()
        if key not in {"device_id", "brand_command", "success"}
    }
    if not status:
        return

    try:
        from app.database.connection import get_db

        synced: tuple[int, dict] | None = None
        with get_db() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE mqtt_topic = ?",
                (mqtt_topic,),
            ).fetchone()
            if device:
                conn.execute(
                    "UPDATE devices SET status_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(status), device["id"]),
                )
                synced = (device["id"], status)
        return synced
    except Exception as exc:
        logger.error("device status sync failed: %s", exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global _main_event_loop
    _main_event_loop = asyncio.get_running_loop()
    logger.info("starting smart home backend")

    init_db()
    logger.info("database initialized")

    init_mqtt()
    subscribe("home/#", on_mqtt_message)
    logger.info("subscribed to MQTT topic home/#")

    rule_engine.reload_rules()

    yield

    stop_mqtt()
    logger.info("backend stopped")


app = FastAPI(
    title="智能家居设备控制系统",
    description="OpenHarmony 智能家居后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(devices.router)
app.include_router(data.router)
app.include_router(rules.router)
app.include_router(scenes.router)
app.include_router(states.router)
app.include_router(login.router)
app.include_router(discovery.router)
app.include_router(bind_device.router)
app.include_router(services.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {
        "name": "智能家居设备控制系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/realtime")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    """Realtime websocket endpoint that requires a valid JWT token."""
    from app.services.security import decode_token

    if not token:
        await ws.close(code=4001, reason="missing token")
        return

    user = decode_token(token)
    if user is None:
        await ws.close(code=4001, reason="invalid token")
        return

    await ws.accept()
    ws_clients.append(ws)
    logger.info("websocket connected for user %s", user.get("username"))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in ws_clients:
            ws_clients.remove(ws)
        logger.info("websocket disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
