# Active Context

## Текущий этап
**Этап 2. Перенос ядра + переход на микросервисы и групповые права.**
Дата: 2026-10-30.

## Что сделано
1. Проанализирован старый Flask/SQLite-контур `edu-math`: 37 таблиц,
   60 шаблонов, веб-маршруты и `/api/v1`, 4 роли, отчёты и выгрузки.
2. Заполнена карта миграции `docs/02-tz/05-karta-migracii.md` (версия 0.2).
3. Создан FastAPI-backend:
   - `/health`, `/api/v1/health`, `/api/v1/meta`, `/docs`, `/openapi.json`;
   - SQLAlchemy 2.0 async + asyncpg + Alembic;
   - миграция `0001_initial` (`iam`, `org`, `audit`);
   - JWT RS256 + refresh-токены с SHA-256, ротацией и отзывом;
   - мультитенантность по `school_id`, запрет cross-tenant;
   - административные эндпоинты: статистика, пользователи, аудит.
4. Реализованы домены этапа 2: LMS, assessment, journal, library; импорт
   старой SQLite; 83 теста, ruff без ошибок.
5. **Микросервисная модель:**
   - реестр `backend/app/services/registry.py` — 14 сервисов, манифесты,
     публикуемые права, зависимости;
   - каталог `system.services` и активации `system.service_activations`;
   - фабрика отдельного приложения `app/service_app.py` (`SERVICE_CODE=...`);
   - API `/api/v1/services/*` и `/api/v1/me/services`.
6. **Групповая модель прав (GBAC):**
   - `iam.groups` на 5 уровнях: country → region → city → school → class;
   - `iam.group_memberships`, `iam.permissions`, `iam.group_permissions`;
   - наследование: явный родитель + организационные предки категории;
   - конфликты: конкретная область побеждает, при равенстве — `deny`;
   - API `/api/v1/groups/*`, `/api/v1/me/permissions`;
   - переходный мост `LEGACY_ROLE_PERMISSIONS` для пользователей без групп.
7. Миграция `0002_groups_permissions_services`; seed создаёт каталог прав,
   сервисы, республиканские активации, школьные и классные группы, членства.
8. Обновлён пакет документации до 0.6: ШК-03-04 (микросервисы),
   ШК-03-05 (группы и права), ШК-04-02 (модель групп и сервисов), ТЗ,
   архитектура, модель данных, API, матрица, план, реестр, журнал.
9. Проект переведён на новый GitHub-репозиторий
   `git@github.com:ruslanadamcuk5/school-platform-v2.git` с отдельным
   deploy-ключом `id_ed25519_school_v2`.

## Что происходит сейчас
- Backend: 83 теста зелёные, `ruff` чистый.
- Миграция `0002` проверена offline (`alembic upgrade head --sql`), но **ещё
  не применена** к пилотной PostgreSQL — требуется подтверждение.
- Seed с группами ещё не прогнан на пилоте.
- Документы обновлены в Markdown; DOCX-пакет 0.6 требует пересборки.

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
1. Подтвердить и применить миграцию `0002` к Stage/пилоту, прогнать seed.
2. Перевести всех пользователей пилота в группы; проверить, что мост
   `LEGACY_ROLE_PERMISSIONS` не используется.
3. Подключить `require_permission`/`require_service` к существующим доменам
   (journal, assessment, library, lms) вместо только ролевых проверок.
4. Динамическое меню фронтенда из `/me/services` и скрытие действий по
   `/me/permissions`.
5. Экран управления группами и экран включения сервисов.
6. Выделить первый сервис (`library`) в отдельный процесс, добавить gateway.
7. Кеширование прав в Redis с инвалидацией; RLS по scope.
8. Пересобрать DOCX-пакет 0.6.

Результат фиксировать в `progress.md`, `docs/02-tz/05-karta-migracii.md` и
журнале изменений.
