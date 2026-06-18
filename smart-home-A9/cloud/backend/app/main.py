"""
FastAPI 入口 — 智能家居设备控制系统后端
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT, DEBUG, CORS_ORIGINS
from app.database import init_db
from app.api import auth, rooms, devices, data, rules
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


async def broadcast_ws(message: dict):
    """向所有已连接的 WebSocket 客户端广播"""
    import json
    text = json.dumps(message)
    for ws in ws_clients[:]:
        try:
            await ws.send_text(text)
        except Exception:
            ws_clients.remove(ws)


def on_mqtt_message(topic: str, payload):
    """MQTT 消息回调：更新规则引擎 + 广播 WebSocket"""
    import json
    # 规则引擎处理
    rule_engine.on_sensor_data(topic, payload)
    # 广播给 WebSocket 客户端
    msg = {"type": "mqtt", "topic": topic, "payload": payload}
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(broadcast_ws(msg))
    except RuntimeError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
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
    """实时数据推送"""
    from app.services.security import decode_token
    if token:
        user = decode_token(token)
        if user is None:
            await ws.close(code=4001, reason="令牌无效")
            return

    await ws.accept()
    ws_clients.append(ws)
    logger.info(f"WebSocket 已连接, 当前 {len(ws_clients)} 个客户端")
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info(f"WebSocket 已断开, 当前 {len(ws_clients)} 个客户端")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
