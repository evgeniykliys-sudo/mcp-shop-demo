"""Простейший token bucket rate limiter — по одному ведру на источник.

В ТЗ (секция 27 "Rate limiting") — отдельный limiter на marketplace +
connection + endpoint group, с Retry-After и exponential backoff.
Здесь один общий bucket на весь upstream — принцип тот же, масштаб меньше.
"""
from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
        self._last_refill = now

    def try_take(self) -> bool:
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False
