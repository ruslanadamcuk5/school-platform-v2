# Architecture Memory

Полная архитектура — в `docs/03-architecture/01-arhitektura.md`.
Микросервисы — в `docs/03-architecture/04-mikroservisy.md`.
Группы и права — в `docs/03-architecture/05-gruppy-i-prava.md`.
Модель данных — в `docs/04-data/01-model-dannyh.md` и `docs/04-data/02-model-grupp-prav-i-servisov.md`.

## Кратко
- Архитектурный стиль: API-first, микросервисы в монорепозитории. На пилоте —
  общий FastAPI-шлюз, в промышленной эксплуатации — отдельный процесс на
  сервис (`app/service_app.py`, `SERVICE_CODE`).
- Клиенты: React SPA, Flutter Android/iOS, PWA.
- Backend: FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2.
- Данные: PostgreSQL 16 (основная БД), Redis (кеш/очереди), S3 (файлы),
  pgvector (поиск по нормативным документам и учебникам).
- Аутентификация: JWT access + refresh, SSO с государственными системами
  (адаптеры).
- Доступ: группы на 5 уровнях (country → region → city → school → class),
  права только группам, наследование по явному родителю и организационным
  предкам категории; при равной глубине `deny` побеждает.
- Мультитенантность: `school_id` + scope-контекст; проверка на API.
- Функционал: реестр `system.services`, активации
  `system.service_activations`; самая конкретная активация побеждает; ядро
  (`system`, `iam`, `org`, `audit`) не отключается.
- Мультиязычность: JSONB-поля контента + i18n интерфейса.
- Офлайн: локальная БД клиента, очередь операций, идемпотентная синхронизация.
- Наблюдаемость: structured logs, метрики, трассировка, аудит действий.

## Границы доменов (сервисы)
1. `system` — реестр сервисов, настройки, языки.
2. `iam` — пользователи, группы, права, сессии, согласия.
3. `org` — регионы, города, школы, классы.
4. `audit` — аудит и события ИБ.
5. `lms` — контент и обучение.
6. `assessment` — тесты и работы.
7. `journal` — расписание, оценки, посещаемость.
8. `library` — библиотека и рекомендации.
9. `analytics` — BI и отчётность.
10. `ai` — ИИ-оркестратор.
11. `communication` — чаты, уведомления, видео.
12. `safety` — психология, инциденты, GPS.
13. `documents` — документы и секретариат.
14. `admin` — административные панели.

## Ключевые модули
- `app/services/registry.py` — манифесты сервисов и каталог прав.
- `app/services/access.py` — разрешение прав и активаций.
- `app/api/deps.py` — `require_permission`, `require_service`,
  `ensure_scope_access`.
- `app/models/iam.py` — группы, членства, права.
- `app/models/system.py` — сервисы и активации.
- `app/api/v1/groups.py`, `me.py`, `services.py` — API управления.
- `app/service_app.py` — фабрика отдельного сервисного приложения.
