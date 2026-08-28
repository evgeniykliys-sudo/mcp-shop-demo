"""Простой in-memory TTL-кэш.

В реальном ТЗ (секция 29 "Cache") — Redis с разным TTL по типу данных.
Здесь тот же принцип на словаре в памяти процесса: достаточно, чтобы
показать сам паттерн (и что ответ всегда помечен cached=true/false).
"""
from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic() + self.ttl_seconds, value)
