"""
pytest fixtures for isolated backend API tests.
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="smart_home_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR / 'test.db'}"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET"] = "test-" + ("0" * 32)

import app.services.mqtt_client  # noqa: E402

_mqtt_import_mocks = [
    patch("app.services.mqtt_client.init_mqtt", MagicMock()),
    patch("app.services.mqtt_client.subscribe", MagicMock()),
    patch("app.services.mqtt_client.publish_message", MagicMock()),
    patch("app.services.mqtt_client.stop_mqtt", MagicMock()),
]
for mock in _mqtt_import_mocks:
    mock.start()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.database.connection import DB_PATH, get_connection  # noqa: E402
from app.main import app  # noqa: E402
from app.services.security import create_token  # noqa: E402

for mock in _mqtt_import_mocks:
    mock.stop()


def pytest_sessionfinish(session, exitstatus):
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

    lifecycle_patches = [
        patch("app.services.mqtt_client.init_mqtt", MagicMock()),
        patch("app.services.mqtt_client.subscribe", MagicMock()),
        patch("app.services.mqtt_client.publish_message", MagicMock()),
        patch("app.services.mqtt_client.stop_mqtt", MagicMock()),
    ]
    for lifecycle_patch in lifecycle_patches:
        lifecycle_patch.start()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        for lifecycle_patch in lifecycle_patches:
            lifecycle_patch.stop()


@pytest.fixture(scope="session")
def auth_headers():
    token = create_token(user_id=1, username="admin", role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db(client):
    conn = get_connection()
    yield conn
    conn.close()
