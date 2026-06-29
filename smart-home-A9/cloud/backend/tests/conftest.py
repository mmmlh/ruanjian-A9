"""
pytest 配置 + 共享 fixtures
使用临时文件数据库，Mock MQTT，不依赖外部服务
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── 在任何 app 模块导入之前设置测试环境变量 ──
TEST_DIR = Path(tempfile.mkdtemp(prefix="smart_home_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR / 'test.db'}"
os.environ["DEBUG"] = "false"

# ── 确保 services 子模块可被 patch 定位 ──
import app.services.mqtt_client  # noqa: E402 — 必须在 patch 之前导入

# ── Mock MQTT 函数（必须在 app.main 导入之前打补丁） ──
_mqtt_mocks = [
    patch("app.services.mqtt_client.init_mqtt", MagicMock()),
    patch("app.services.mqtt_client.subscribe", MagicMock()),
    patch("app.services.mqtt_client.publish_message", MagicMock()),
    patch("app.services.mqtt_client.stop_mqtt", MagicMock()),
]
for m in _mqtt_mocks:
    m.start()

# ── 现在安全导入 ──
from fastapi.testclient import TestClient
from app.main import app
from app.services.security import create_token


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后的清理"""
    for m in _mqtt_mocks:
        m.stop()
    shutil.rmtree(TEST_DIR, ignore_errors=True)


# ══════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════

@pytest.fixture(scope="session")
def client():
    """返回 TestClient — 整个测试会话共享，lifespan 只执行一次"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers():
    """返回已认证的请求头"""
    token = create_token(user_id=1, username="admin", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db():
    """返回可查询的数据库连接（每次测试独立）"""
    from app.database.connection import get_connection
    conn = get_connection()
    yield conn
    conn.close()
