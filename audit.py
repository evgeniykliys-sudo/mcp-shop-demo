"""Аудит-лог вызовов tools в SQLite.

В ТЗ (секция 32 "Аудит") — обязательное логирование каждого вызова
(READ: timestamp/client/tool/duration/result; WRITE: ещё и before/after).
Это демо только read-only, поэтому логируем базовый набор полей.
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool TEXT NOT NULL,
    params TEXT,
    duration_ms INTEGER NOT NULL,
    result_status TEXT NOT NULL
);
"""


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(SCHEMA)


@contextmanager
def timed_call():
    start = time.monotonic()
    result = {"status": "success"}
    try:
        yield result
    except Exception:
        result["status"] = "error"
        raise
    finally:
        result["duration_ms"] = int((time.monotonic() - start) * 1000)


def log_call(tool: str, params: str, duration_ms: int, result_status: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO tool_calls (timestamp, tool, params, duration_ms, result_status) "
            "VALUES (datetime('now'), ?, ?, ?, ?)",
            (tool, params, duration_ms, result_status),
        )
