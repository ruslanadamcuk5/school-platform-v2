# Active Context

## Текущий этап
**Этап 1. Анализ и пилотный backend — завершён.**
Дата: 2026-10-27.

## Что сделано
1. Проанализирован старый Flask/SQLite-контур `edu-math`: 37 таблиц,
   60 шаблонов, веб-маршруты и `/api/v1`, 4 роли, отчёты и выгрузки.
2. Заполнена карта миграции `docs/02-tz/05-karta-migracii.md` (версия 0.2):
   таблицы, API, шаблоны, роли, отчёты, порядок переноса, контроль качества.
3. Создан FastAPI-backend:
   - `/health`, `/api/v1/health`, `/api/v1/meta`, `/docs`, `/openapi.json`;
   - SQLAlchemy 2.0 async + asyncpg + Alembic;
   - миграция `0001_initial` (`iam`, `org`, `audit`);
   - JWT RS256 + refresh-токены с SHA-256, ротацией и отзывом;
   - RBAC: superadmin, admin, methodologist, teacher, student, parent,
     psychologist, secretary;
   - мультитенантность по `school_id`, запрет cross-tenant;
   - административные эндпоинты: статистика, пользователи, аудит.
4. Применена миграция к пилотной PostgreSQL, созданы школа, классы 1–11,
   супер-администратор.
5. Выполнены проверки: 7 unit-тестов, ruff, интеграционный smoke:
   login, `/me`, школы, классы, статистика, cross-tenant 403, RBAC 403,
   ротация refresh, logout.
6. Пилотный сайт `https://school-platform-v2.185.31.40.24.nip.io` переключён
   с Static files на User program (Uvicorn).
7. Старый сайт `https://virusadk.alwaysdata.net` остаётся доступным (200),
   его конфигурация и процессы не менялись.
8. Обновлены README, API-документ, отчёт этапа 1, журнал изменений,
   реестр документов, Word-пакет.

## Что происходит сейчас
Этап 1 закрыт. Пилотный API и БД доступны. Следующий этап — перенос ядра:
справочники, пользователи, LMS, Assessment, Journal.

## Фактические параметры пилота
- Backend: `/home/virusadk/school-platform-v2/backend`.
- Venv: `/home/virusadk/.virtualenvs/school-platform`.
- Working directory в панели Alwaysdata: `school-platform-v2/backend`
  (относительно `/home/virusadk`, абсолютный путь панель удваивает).
- Команда: `uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers`.
- Кэш сайта отключён; WAF basic; Force HTTPS включён.
- `robots.txt` закрывает пилот от индексации; добавлены security headers.

## Запреты
- Не трогать работающий проект `C:\Users\adamrv\Documents\edu-math`.
- Не менять его базу и не перезапускать его процессы.
- Не менять сайт `virusadk.alwaysdata.net`.
- Не переносить реальные ПДн в новую систему без согласованной политики.
- Не коммитить `.env`, `backend/.env`, `secrets/`, пароли и приватные ключи.

## Следующая задача
1. Спроектировать и создать миграции доменов `lms`, `assessment`, `journal`.
2. Перенести справочники: регионы, города, школы, классы, предметы.
3. Перенести пользователей и связи родитель-ребёнок.
4. Перенести темы, методики, учебники и файлы.
5. Начать React-клиент: login, кабинеты, API-клиент.
6. Подключить Redis и rate limiting.

Результат фиксировать в `progress.md`, `docs/02-tz/05-karta-migracii.md` и
журнале изменений.
