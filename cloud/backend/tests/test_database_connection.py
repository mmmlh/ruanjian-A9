import sqlite3

from app.database.connection import (
    SQLITE_BUSY_TIMEOUT_MS,
    configure_journal_mode,
    get_connection,
)


def test_connection_enables_foreign_keys_and_waits_for_busy_database(client):
    conn = get_connection()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == SQLITE_BUSY_TIMEOUT_MS
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        conn.close()


def test_configure_journal_mode_migrates_wal_database(tmp_path):
    db_path = tmp_path / "wal.db"
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        configure_journal_mode(conn)
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        conn.close()
