from pathlib import Path

import app.database.connection as connection


def test_get_connection_uses_configured_journal_mode(tmp_path, monkeypatch):
    db_path = Path(tmp_path) / "journal-mode.db"
    monkeypatch.setattr(connection, "DB_PATH", str(db_path))
    monkeypatch.setattr(connection, "SQLITE_JOURNAL_MODE", "DELETE", raising=False)

    conn = connection.get_connection()
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        conn.close()
