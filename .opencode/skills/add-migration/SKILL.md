---
name: add-migration
description: Добавить миграцию Alembic для изменения схемы PostgreSQL с offline SQL, downgrade и тестами
---

## Когда использовать
Любое изменение схемы БД: новая таблица, колонка, индекс, FK, enum.

## Порядок
1. Измени модель в `backend/app/models/`.
2. Изучи последнюю миграцию в `backend/alembic/versions/` и `alembic heads`.
3. Создай ревизию:
   ```powershell
   cd backend
   ..\.venv\Scripts\python.exe -m alembic revision -m "краткое имя"
   ```
4. Заполни `upgrade()` и `downgrade()`; для новых таблиц соблюдай порядок FK:
   сначала таблицы, затем FK, в downgrade — наоборот.
5. Проверь offline SQL:
   ```powershell
   ..\.venv\Scripts\python.exe -m alembic upgrade head --sql
   ```
6. Обнови модели, `docs/04-data/01-model-dannyh.md`, журнал изменений.
7. Тесты: миграция и затронутые API;
   `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1`.

## Запреты
- Не применять миграцию к пилоту без отдельной явной команды.
- Не менять уже применённую ревизию; создавай новую.
- Не оставлять `downgrade()` пустым, если это возможно.
