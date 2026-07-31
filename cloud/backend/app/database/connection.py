"""
SQLite 数据库连接管理
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from app.config import DATABASE_URL

# 从 DATABASE_URL 提取文件路径
DB_PATH = DATABASE_URL.replace("sqlite:///", "")
SQLITE_BUSY_TIMEOUT_SECONDS = 30
SQLITE_BUSY_TIMEOUT_MS = SQLITE_BUSY_TIMEOUT_SECONDS * 1000


def get_connection() -> sqlite3.Connection:
    """获取数据库连接（锁等待 + 外键约束）。"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def configure_journal_mode(conn: sqlite3.Connection) -> None:
    """Use a journal mode compatible with Docker Desktop bind mounts."""
    current_mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
    if current_mode == "wal":
        busy, _, _ = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise sqlite3.OperationalError("cannot checkpoint SQLite WAL: database is busy")

    journal_mode = conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower()
    if journal_mode != "delete":
        raise sqlite3.OperationalError(
            f"failed to enable SQLite DELETE journal mode: {journal_mode}"
        )


@contextmanager
def get_db():
    """上下文管理器：自动提交/回滚"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """建表 + 插入初始数据"""
    from .init_db import create_tables, seed_data
    with get_db() as conn:
        configure_journal_mode(conn)
        create_tables(conn)
        seed_data(conn)
