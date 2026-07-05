"""L3 · 长期事实（SQLite）

存储位置：~/.qingqiu/memory/facts.sqlite
表结构：
  facts(key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at REAL, updated_at REAL)
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class L3FactsMemory:
    """L3 · SQLite 长期事实记忆"""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @property
    def name(self) -> str:
        return "L3"

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _init_db(self) -> None:
        """建 facts 表（如不存在）"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> str | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT value FROM facts WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        now = time.time()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO facts (key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now, now),
            )
            conn.commit()

    def delete(self, key: str) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("DELETE FROM facts WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def list_keys(self) -> list[str]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT key FROM facts ORDER BY key").fetchall()
            return [row[0] for row in rows]

    def count(self) -> int:
        """总记录数（调试用）"""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM facts").fetchone()
            return row[0] if row else 0

    def get_with_metadata(self, key: str) -> dict[str, str | float] | None:
        """带元数据查询（调试 / UI 用）"""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT key, value, created_at, updated_at FROM facts WHERE key = ?",
                (key,),
            ).fetchone()
            if not row:
                return None
            return {
                "key": row[0],
                "value": row[1],
                "created_at": row[2],
                "updated_at": row[3],
            }