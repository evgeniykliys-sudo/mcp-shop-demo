"""Сквозной тест: поднимает server.py как настоящий MCP-процесс через stdio
и обращается к нему протоколом MCP — так же, как это делал бы Claude Code
или другой MCP-клиент. Не мок, а реальный процесс + реальный HTTP к upstream.
"""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== tools/list ===")
            for t in tools.tools:
                print(f"- {t.name}: {t.description[:70]}...")

            print("\n=== rate limit: 8 запросов подряд первым делом, capacity=5 — часть должна словить RATE_LIMITED ===")
            statuses = []
            for _ in range(8):
                r = await session.call_tool("shop_categories_get", {})
                statuses.append(json.loads(r.content[0].text)["success"])
            print("успехов:", sum(statuses), "из", len(statuses), "->", statuses)

            print("\n(пауза 5с, чтобы bucket восстановился перед функциональными проверками)")
            await asyncio.sleep(5)

            print("\n=== shop_categories_get ===")
            r = await session.call_tool("shop_categories_get", {})
            print(r.content[0].text)

            print("\n=== shop_products_list(limit=3) ===")
            r = await session.call_tool("shop_products_list", {"limit": 3})
            print(r.content[0].text)

            print("\n=== shop_product_get(product_id='1') — второй вызов должен быть cached=true ===")
            r1 = await session.call_tool("shop_product_get", {"product_id": "1"})
            print(r1.content[0].text)
            r2 = await session.call_tool("shop_product_get", {"product_id": "1"})
            data2 = json.loads(r2.content[0].text)
            print("cached второй раз:", data2.get("meta", {}).get("cached"))

            print("\n=== shop_product_get(product_id='99999') — ожидаем NOT_FOUND ===")
            r = await session.call_tool("shop_product_get", {"product_id": "99999"})
            print(r.content[0].text)

            print("\n=== shop_products_list(limit=999) — ожидаем INVALID_ARGUMENT ===")
            r = await session.call_tool("shop_products_list", {"limit": 999})
            print(r.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
