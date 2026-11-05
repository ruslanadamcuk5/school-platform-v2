---
description: Показать схему таблицы через read-only запрос
---

Покажи схему таблицы `$ARGUMENTS`:

- колонки, типы, nullable, default;
- первичный ключ, индексы, внешние ключи;
- ограничения.

Используй read-only подключение (`psql` или asyncpg). Не читай
`docs/04-data/01-model-dannyh.md` целиком и не выполняй DDL/DML.
