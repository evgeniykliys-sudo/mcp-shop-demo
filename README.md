# mcp-shop-demo

Учебный MCP-сервер (read-only), написанный после разбора реального
production ТЗ на MCP-сервер для Wildberries/Ozon/Яндекс.Маркета. Настоящих
продавцовских API-ключей нет и не нужно — источник данных здесь публичный
тестовый каталог товаров ([fakestoreapi.com](https://fakestoreapi.com)),
важен не он, а форма, в которой AI-клиент получает данные, и что каждый
вызов проверяется и логируется.

Что показывает:
- нормализованный ответ (`success/data/meta` с `fetched_at`/`source`/`cached`)
- единая модель ошибок (`NOT_FOUND`, `INVALID_ARGUMENT`, `RATE_LIMITED`, ...)
- кэш с TTL
- rate limiting (token bucket)
- аудит-лог каждого вызова в SQLite

Подробнее, что упрощено по сравнению с реальным продакшн-ТЗ — в
[ARCHITECTURE.md](ARCHITECTURE.md).

## Запуск

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt   # Linux/Mac
```

Сервер общается по протоколу MCP через stdio — сам по себе процесс
ничего не печатает и не открывает порт, его должен запускать MCP-клиент.

## Подключение к Claude Code / Claude Desktop

Добавить в `.mcp.json` (Claude Code) или конфиг Claude Desktop:

```json
{
  "mcpServers": {
    "shop-demo": {
      "command": "C:/путь/до/mcp-shop-demo/venv/Scripts/python.exe",
      "args": ["C:/путь/до/mcp-shop-demo/server.py"]
    }
  }
}
```

После этого в чате доступны инструменты `shop_products_list`,
`shop_product_get`, `shop_categories_get`.

## Тест без Claude — сквозной клиент

```bash
venv\Scripts\python test_client.py
```

Поднимает `server.py` как настоящий MCP-процесс (stdio) и стучится в него
по протоколу MCP — так же, как это делал бы любой MCP-клиент: список
tools, обычные вызовы, проверка кэша (второй вызов с тем же id — `cached:
true`), проверка `NOT_FOUND`/`INVALID_ARGUMENT`, проверка rate limit (из 8
запросов подряд проходят первые 5 — по размеру bucket).

## Аудит

Каждый вызов инструмента пишется в `audit.db` (SQLite,
таблица `tool_calls`): время, tool, параметры, длительность, статус.
