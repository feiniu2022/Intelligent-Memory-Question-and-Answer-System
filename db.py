"""SQLite 数据库管理：用户表 + 审计日志表"""
import sqlite3
import threading
from datetime import datetime
from typing import Optional

from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(settings.resolved_db_path), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request_summary TEXT,
            response_summary TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
    """)
    conn.commit()
    logger.info("数据库初始化完成")


def create_user(username: str, hashed_password: str) -> int:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
        (username, hashed_password),
    )
    conn.commit()
    return cursor.lastrowid


def get_user_by_username(username: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def log_audit(
    user_id: str,
    action: str,
    endpoint: str,
    request_summary: str = "",
    response_summary: str = "",
    ip_address: str = "",
):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, endpoint, request_summary, response_summary, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, action, endpoint, request_summary[:500], response_summary[:500], ip_address),
    )
    conn.commit()


def query_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    conn = _get_conn()
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)
    if action:
        sql += " AND action = ?"
        params.append(action)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]