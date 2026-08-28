# TODO: mcp-shop-demo

- [x] MCP-сервер на STDIO с 3 read-only tools
- [x] Нормализованный ответ (success/data/meta) и единая модель ошибок
- [x] TTL-кэш
- [x] Rate limiting (token bucket)
- [x] Аудит-лог вызовов в SQLite
- [x] Сквозной тест через настоящий MCP-протокол (test_client.py)
- [x] README + ARCHITECTURE с явным сравнением с реальным production ТЗ
- [x] Залить на GitHub, добавить ссылку в FREELANCE.md
- [ ] Опционально: второй transport — Streamable HTTP (уже настоящий сетевой
      сервис → тогда осмысленно добавить Dockerfile/docker-compose)
- [ ] Опционально: второй источник данных (второй "адаптер") — показать,
      что паттерн масштабируется на несколько источников с общим слоем
