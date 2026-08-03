"""
SQLite 数据库连接管理
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from app.config import DATABASE_URL, SQLITE_JOURNAL_MODE

# 从 DATABASE_URL 提取文件路径
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

def get_connection() -> sqlite3.Connection:
    """获取数据库连接（使用配置的日志模式 + 外键约束）"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    if SQLITE_JOURNAL_MODE not in {"WAL", "DELETE"}:
        conn.close()
        raise ValueError("SQLITE_JOURNAL_MODE must be WAL or DELETE")
    conn.execute(f"PRAGMA journal_mode={SQLITE_JOURNAL_MODE}")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

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
        create_tables(conn)
        seed_data(conn)
