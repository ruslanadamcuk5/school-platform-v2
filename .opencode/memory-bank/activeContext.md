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
Этап 1 закрыт. Идёт этап 2 — перенос ядра. Уже готовы миграции доменов
`lms`, `assessment`, `journal`, `analytics`, `ai`, `communication`,
идемпотентный импорт старой SQLite и API чтения учебного контента:
`/api/v1/lms/subjects`, `/topics`, `/textbooks`, `/courses`.
Все 13 тестов проходят, `ruff` без ошибок.

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
1. Реализовать API тестов и работ: `/assessment/quizzes`, `/assignments`,
   `/submissions`, прохождение и результаты.
2. Реализовать API журнала: расписание и оценки/посещаемость (`/journal/*`).
3. Реализовать API библиотеки и рекомендаций (`/library/*`).
4. Реализовать кабинеты: `/teacher/*`, `/student/*`, `/parent/*`.
5. Прогнать `app.db.import_legacy` на Stage и сверить контрольные суммы.
6. Начать React-клиент: login, кабинеты, API-клиент.
7. Подключить Redis и rate limiting.

Результат фиксировать в `progress.md`, `docs/02-tz/05-karta-migracii.md` и
журнале изменений.
