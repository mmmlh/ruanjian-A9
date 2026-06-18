"""
应用配置 — 通过环境变量覆盖默认值
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ── 数据库 ──
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'smart_home.db'}")

# ── MQTT ──
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TLS_PORT = int(os.getenv("MQTT_TLS_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"

# ── JWT ──
JWT_SECRET = os.getenv("JWT_SECRET", "smart-home-a9-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# ── AES ──
AES_KEY_SIZE = 32  # 256 bits
AES_BLOCK_SIZE = 16

# ── 服务器 ──
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# ── CORS ──
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
