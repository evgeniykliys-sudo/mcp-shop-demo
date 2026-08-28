"""Общие модели ответа: нормализованный envelope и единая модель ошибок.

Паттерн взят из реального production ТЗ на MCP-сервер для маркетплейсов
(см. секции 16 "Нормализованный формат ответа" и 31 "Единая error model") —
здесь воспроизведён в уменьшенном виде на одном источнике данных.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ok(data: Any, *, source: str, cached: bool = False) -> dict:
    return {
        "success": True,
        "data": data,
        "meta": {
            "fetched_at": now_iso(),
            "source": source,
            "cached": cached,
        },
    }


def error(code: str, message: str, *, retryable: bool = False) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
    }


# Единый набор кодов ошибок — подмножество из ТЗ, актуальное для read-only демо.
NOT_FOUND = "NOT_FOUND"
INVALID_ARGUMENT = "INVALID_ARGUMENT"
UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
UPSTREAM_UNAVAILABLE = "MARKETPLACE_UNAVAILABLE"
RATE_LIMITED = "RATE_LIMITED"
