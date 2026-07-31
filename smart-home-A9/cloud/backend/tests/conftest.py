"""
pytest fixtures for isolated backend API tests.
"""
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="smart_home_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR / 'test.db'}"
os.environ["DEBUG"] = "false"

import app.services.mqtt_client  # noqa: E402

_real_mqtt = SimpleNamespace(
    init_mqtt=app.services.mqtt_client.init_mqtt,
    publish_message=app.services.mqtt_client.publish_message,
    subscribe=app.services.mqtt_client.subscribe,
    stop_mqtt=app.services.mqtt_client.stop_mqtt,
)

_mqtt_mocks = [
    patch("app.services.mqtt_client.init_mqtt", MagicMock()),
    patch("app.services.mqtt_client.subscribe", MagicMock()),
    patch("app.services.mqtt_client.publish_message", MagicMock()),
    patch("app.services.mqtt_client.stop_mqtt", MagicMock()),
]
for mock in _mqtt_mocks:
    mock.start()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.database.connection import DB_PATH, get_connection  # noqa: E402
from app.main import app  # noqa: E402
from app.services.security import create_token  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    for mock in _mqtt_mocks:
        mock.stop()
    shutil.rmtree(TEST_DIR, ignore_errors=True)


@pytest.fixture(scope="function")
def client():
    db_file = Path(DB_PATH)
    wal_file = Path(f"{DB_PATH}-wal")
    shm_file = Path(f"{DB_PATH}-shm")

    for path in (db_file, wal_file, shm_file):
        if path.exists():
            path.unlink()

    init_db()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_headers():
    token = create_token(user_id=1, username="admin", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def real_mqtt_functions():
    return _real_mqtt


@pytest.fixture(scope="function")
def db(client):
    conn = get_connection()
    yield conn
    conn.close()
