# Архитектура

```
MCP-клиент (Claude Code / test_client.py)
        │  stdio, протокол MCP
        ▼
   server.py  (mcp.server.mcpserver.MCPServer, 3 tools)
        │
        ▼
   _call()  — общая обёртка на каждый tool:
        │     1. rate limit (TokenBucket) → RATE_LIMITED
        │     2. вызов tool-функции
        │     3. аудит в SQLite (всегда, даже при ошибке)
        │
        ├─→ cache.py (TTLCache, in-memory) — если есть свежее значение,
        │             upstream не дёргаем
        │
        └─→ httpx → fakestoreapi.com (публичный источник, без ключей)
```

Каждый ответ — либо `models.ok(...)`, либо `models.error(...)`: AI-клиент
всегда получает одну и ту же форму, а не сырой ответ upstream API.

## Откуда это взято

Этот проект — не с нуля выдуманная архитектура, а сознательно уменьшенная
копия паттернов из реального production ТЗ на MCP-сервер для
Wildberries/Ozon/Яндекс.Маркета (см. оценку ТЗ в переписке). В таблице —
что оттуда взято и что упрощено.

| Паттерн из ТЗ | Что в ТЗ (прод) | Что здесь (демо) |
|---|---|---|
| Нормализованный ответ | `success/data/meta`, флаг `cached`, курсорная пагинация | то же самое, один источник вместо трёх |
| Единая error model | ~15 кодов ошибок, `retryable` | 5 кодов, тот же принцип |
| Rate limiting | отдельный limiter на marketplace+connection+endpoint, Redis, Retry-After | один общий token bucket в памяти процесса |
| Кэш | Redis, TTL по типу данных (цены/остатки/справочники — разный TTL) | in-memory словарь, единый TTL |
| Аудит | PostgreSQL, READ+WRITE поля (before/after, confirmation), retention | SQLite, только READ-поля (tool/params/duration/status) |
| Multi-account / connections | `connections_list`, изоляция между кабинетами, security-тест на утечку | не реализовано — источник один и без авторизации |
| Секьюрити секретов | Vault/KMS, запрет секретов в логах/ответах | секретов нет вообще (публичный API без ключа) |
| Write-операции (preview/confirmation/idempotency) | обязательны для update_price и т.п. | не реализовано — сервер полностью read-only |
| Транспорт | Streamable HTTP (production), STDIO (dev) | только STDIO — это локальный dev-инструмент для MCP-клиента, не сетевой сервис |

## Почему без Docker

Остальные проекты в портфолио (боты) — долгоживущие сетевые процессы,
для них Docker даёт реальный смысл (изоляция, деплой на сервер, restart
policy). MCP-сервер на STDIO — не сетевой сервис: клиент (Claude Code/
Claude Desktop) сам запускает его как локальный подпроцесс через
`command`+`args`. Заворачивать это в контейнер ради галочки было бы
искусственно; production-вариант с транспортом Streamable HTTP (уже
реальный сетевой сервис, вот там Docker был бы уместен) — в TODO.md как
возможное развитие.
