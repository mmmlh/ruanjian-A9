"""
FastAPI 入口 — 智能家居设备控制系统后端
"""
import json
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT, DEBUG, CORS_ORIGINS
from app.database import init_db
from app.api import auth, rooms, devices, data, rules, scenes
from app.services.mqtt_client import init_mqtt, subscribe, stop_mqtt
from app.services.rule_engine import rule_engine

# 日志配置
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── WebSocket 连接管理 ──
ws_clients: list[WebSocket] = []
_main_event_loop: asyncio.AbstractEventLoop | None = None


async def broadcast_ws(message: dict):
    """向所有已连接的 WebSocket 客户端广播"""
    text = json.dumps(message)
    for ws in ws_clients[:]:
        try:
            await ws.send_text(text)
        except Exception:
            ws_clients.remove(ws)


def on_mqtt_message(topic: str, payload):
    """MQTT 消息回调：更新规则引擎 + 广播 WebSocket + 持久化
    注意：此函数在 Paho MQTT 网络线程中调用，不可直接操作 asyncio 对象
    """
    # 规则引擎处理
    rule_engine.on_sensor_data(topic, payload)

    # 广播给 WebSocket 客户端（通过线程安全方式投递到主事件循环）
    msg = {"type": "mqtt", "topic": topic, "payload": payload}
    if _main_event_loop and _main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_ws(msg), _main_event_loop)

    # 持久化传感器数据 + 同步设备状态
    _persist_sensor_data(topic, payload)
    _sync_device_status(topic, payload)


def _persist_sensor_data(topic: str, payload):
    """将传感器数据写入 sensor_data 表"""
    # 只处理 sensor 主题: home/{room_id}/{device_type}/sensor
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return
    parts = topic.split("/")
    if len(parts) < 4 or parts[-1] != "sensor":
        return
    room_id = parts[1]       # e.g. "livingroom"
    device_type = parts[2]   # e.g. "temperature_sensor"
    mqtt_topic = f"home/{room_id}/{device_type}"

    # 确定 data_type 和 value
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
                "SELECT id FROM devices WHERE mqtt_topic = ?", (mqtt_topic,)
            ).fetchone()
            if device:
                conn.execute(
                    "INSERT INTO sensor_data (device_id, data_type, value, extra_json) "
                    "VALUES (?, ?, ?, ?)",
                    (device["id"], data_type, value, json.dumps(extra)),
                )
    except Exception as e:
        logger.error(f"传感器数据持久化失败: {e}")


def _sync_device_status(topic: str, payload):
    """将设备状态更新同步到 devices 表的 status_json 字段"""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return
    # 只处理 status 主题: home/{room_id}/{device_type}/status
    parts = topic.split("/")
    if len(parts) < 4 or parts[-1] != "status":
        return
    room_id = parts[1]
    device_type = parts[2]
    mqtt_topic = f"home/{room_id}/{device_type}"

    # 提取设备状态字段（过滤掉内部字段）
    status = {k: v for k, v in payload.items() if k not in ("device_id", "brand_command")}

    if not status:
        return

    try:
        from app.database.connection import get_db
        with get_db() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE mqtt_topic = ?", (mqtt_topic,)
            ).fetchone()
            if device:
                conn.execute(
                    "UPDATE devices SET status_json = ? WHERE id = ?",
                    (json.dumps(status), device["id"]),
                )
    except Exception as e:
        logger.error(f"设备状态同步失败: {e}")




@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _main_event_loop
    _main_event_loop = asyncio.get_running_loop()
    logger.info("正在启动智能家居后端服务...")

    # 初始化数据库
    init_db()
    logger.info("数据库初始化完成")

    # 初始化 MQTT
    init_mqtt()
    subscribe("home/#", on_mqtt_message)
    logger.info("MQTT 订阅已设置: home/#")

    # 加载规则
    rule_engine.reload_rules()

    yield

    # 关闭
    stop_mqtt()
    logger.info("后端服务已停止")


# ── FastAPI 应用 ──
app = FastAPI(
    title="智能家居设备控制系统",
    description="基于 OpenHarmony 的智能家居后端 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(devices.router)
app.include_router(data.router)
app.include_router(rules.router)
app.include_router(scenes.router)


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


# ── WebSocket 端点 ──
@app.websocket("/ws/realtime")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    """实时数据推送 — 需要有效的 JWT token"""
    from app.services.security import decode_token
    if not token:
        await ws.close(code=4001, reason="缺少认证令牌")
        return
    user = decode_token(token)
    if user is None:
        await ws.close(code=4001, reason="令牌无效或已过期")
        return

    await ws.accept()
    ws_clients.append(ws)
    logger.info(f"WebSocket 已连接 (用户: {user.get('username')}), 当前 {len(ws_clients)} 个客户端")
    try:
        while True:
            # 保持连接，接收客户端消息（ping/keepalive）
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info(f"WebSocket 已断开, 当前 {len(ws_clients)} 个客户端")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
