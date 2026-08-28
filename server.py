"""mcp-shop-demo — учебный MCP-сервер, read-only.

Идея: тот же набор паттернов, что требует реальное production ТЗ на
MCP-сервер для маркетплейсов (нормализованный ответ, единая модель ошибок,
кэш с TTL, rate limit, аудит-лог), но на одном открытом источнике данных
(fakestoreapi.com — публичный тестовый каталог товаров, без ключей и
реального продавца) и без write-операций, очередей, Redis и т.д.

Источник данных здесь не важен сам по себе — важна форма ответа, в которой
AI-клиент получает данные, и то, что каждый вызов проверяется на rate limit
и попадает в аудит-лог.
"""
from __future__ import annotations

import json
import time

import httpx
from mcp.server.mcpserver import MCPServer

import audit
import models
from cache import TTLCache
from ratelimit import TokenBucket

UPSTREAM = "https://fakestoreapi.com"
SOURCE_NAME = "fakestoreapi_demo"

cache = TTLCache(ttl_seconds=60)
bucket = TokenBucket(capacity=5, refill_per_second=1)  # 5 запросов сразу, потом 1/сек

mcp = MCPServer("shop-demo")


def _call(tool: str, params: dict, fn):
    """Общая обёртка: rate limit -> вызов -> аудит. Всё сквозь неё."""
    if not bucket.try_take():
        result = models.error(models.RATE_LIMITED, "Превышен лимит запросов, попробуйте через секунду", retryable=True)
        audit.log_call(tool, json.dumps(params, ensure_ascii=False), 0, "rate_limited")
        return result

    start = time.monotonic()
    status = "error"  # переопределяется ниже; остаётся "error", если fn() бросит что-то неучтённое
    try:
        result = fn()
        status = "success" if result.get("success") else "error"
        return result
    except httpx.TimeoutException:
        status = "error"
        return models.error(models.UPSTREAM_TIMEOUT, "Источник данных не ответил вовремя", retryable=True)
    except httpx.HTTPError:
        status = "error"
        return models.error(models.UPSTREAM_UNAVAILABLE, "Источник данных недоступен", retryable=True)
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        audit.log_call(tool, json.dumps(params, ensure_ascii=False), duration_ms, status)


@mcp.tool()
def shop_products_list(limit: int = 10, cursor: str | None = None) -> dict:
    """Список товаров каталога. Пагинация нормализована под единый вид
    (limit/cursor на входе, items/next_cursor/has_more на выходе), хотя
    сам upstream API пагинации не поддерживает — это демонстрация паттерна
    из ТЗ: AI не должен знать специфику пагинации конкретного источника."""

    def run():
        if limit < 1 or limit > 50:
            return models.error(models.INVALID_ARGUMENT, "limit должен быть от 1 до 50")

        cache_key = f"products_list:{limit}:{cursor or 0}"
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return models.ok(cached_value, source=SOURCE_NAME, cached=True)

        offset = int(cursor) if cursor else 0
        resp = httpx.get(f"{UPSTREAM}/products", timeout=5)
        resp.raise_for_status()
        all_products = resp.json()

        page = all_products[offset : offset + limit]
        has_more = offset + limit < len(all_products)
        data = {
            "items": [
                {
                    "product_id": str(p["id"]),
                    "title": p["title"],
                    "category": p["category"],
                    "price": {"amount": f"{p['price']:.2f}", "currency": "USD"},
                }
                for p in page
            ],
            "next_cursor": str(offset + limit) if has_more else None,
            "has_more": has_more,
        }
        cache.set(cache_key, data)
        return models.ok(data, source=SOURCE_NAME, cached=False)

    return _call("shop_products_list", {"limit": limit, "cursor": cursor}, run)


@mcp.tool()
def shop_product_get(product_id: str) -> dict:
    """Данные одного товара по id. Возвращает NOT_FOUND, если товара нет —
    не бросает низкоуровневую ошибку HTTP наружу к AI-клиенту."""

    def run():
        cache_key = f"product_get:{product_id}"
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return models.ok(cached_value, source=SOURCE_NAME, cached=True)

        resp = httpx.get(f"{UPSTREAM}/products/{product_id}", timeout=5)
        if resp.status_code == 404 or resp.text.strip() == "":
            return models.error(models.NOT_FOUND, f"Товар {product_id} не найден")
        resp.raise_for_status()
        p = resp.json()
        data = {
            "product_id": str(p["id"]),
            "title": p["title"],
            "category": p["category"],
            "price": {"amount": f"{p['price']:.2f}", "currency": "USD"},
            "rating": p.get("rating", {}),
        }
        cache.set(cache_key, data)
        return models.ok(data, source=SOURCE_NAME, cached=False)

    return _call("shop_product_get", {"product_id": product_id}, run)


@mcp.tool()
def shop_categories_get() -> dict:
    """Список категорий каталога."""

    def run():
        cache_key = "categories_get"
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return models.ok(cached_value, source=SOURCE_NAME, cached=True)

        resp = httpx.get(f"{UPSTREAM}/products/categories", timeout=5)
        resp.raise_for_status()
        data = {"categories": resp.json()}
        cache.set(cache_key, data)
        return models.ok(data, source=SOURCE_NAME, cached=False)

    return _call("shop_categories_get", {}, run)


if __name__ == "__main__":
    audit.init_db()
    mcp.run(transport="stdio")
