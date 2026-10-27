# ЕООП «Школьник» — school-platform-v2

Новая версия единой общеобразовательной обучающей платформы для Республики
Беларусь. Проект создаётся как преемник работающего Flask/SQLite-приложения:
существующий функционал переносится поэтапно, без остановки текущего сервиса.

## Текущий статус

**Этап 0 — инициализация завершена.**
**Этап 1 — анализ и пилотный backend завершён.**

Созданы структура проекта, документация, GitHub-репозиторий, отдельная база
PostgreSQL и отдельный пилотный сайт на Alwaysdata. Реализован FastAPI-backend
с health-check, OpenAPI, SQLAlchemy 2.0 async, Alembic, JWT, RBAC и
мультитенантностью по `school_id`. Пилотный сайт переключён с Static files на
User program (Uvicorn). Старый сайт `virusadk.alwaysdata.net` продолжает
работать без изменений.

### Пилотные ресурсы

| Ресурс | Адрес / значение |
|---|---|
| GitHub | `https://github.com/newvirusadk-cmd/school-platform-v2` (private) |
| Пилотный API | `https://school-platform-v2.185.31.40.24.nip.io` |
| Health | `https://school-platform-v2.185.31.40.24.nip.io/health` |
| Swagger UI | `https://school-platform-v2.185.31.40.24.nip.io/docs` |
| OpenAPI | `https://school-platform-v2.185.31.40.24.nip.io/openapi.json` |
| PostgreSQL | `postgresql-virusadk.alwaysdata.net:5432/virusadk_school_platform` |
| Старый сайт (не изменять) | `https://virusadk.alwaysdata.net` |
| Документация Word | `docs/word/` |

Пароли и ключи хранятся только в локальном `.env`, `backend/.env` на сервере и
`secrets/` (исключены из Git). Пароль супер-администратора — в `.env`
(`ADMIN_PASSWORD`), логин — `ADMIN_LOGIN` (по умолчанию `admin`).

## Целевой стек

- Backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16+ + Redis.
- Web: React + TypeScript + Vite + TailwindCSS.
- Mobile: Flutter (Android/iOS).
- AI: OpenRouter / DeepSeek.
- Файлы: S3-совместимое хранилище.

## Что уже работает

- `GET /health`, `GET /api/v1/health` — проверка API и БД.
- `GET /api/v1/meta` — версия, языки, feature flags.
- `POST /api/v1/auth/login` — JWT access + refresh.
- `POST /api/v1/auth/refresh` — ротация refresh-токена.
- `POST /api/v1/auth/logout` — отзыв refresh-токена.
- `GET /api/v1/auth/me` — текущий пользователь.
- `GET /api/v1/org/schools`, `/org/classes` — школы и классы с tenant-проверкой.
- `GET /api/v1/admin/stats`, `/admin/users`, `/admin/audit` — администрирование.
- `POST /api/v1/admin/users` — создание пользователя школы.
- Роли: `superadmin`, `admin`, `methodologist`, `teacher`, `student`, `parent`,
  `psychologist`, `secretary`.
- Пилотная школа и классы 1–11 в PostgreSQL.

## Структура

```text
school-platform-v2/
├── opencode.json
├── AGENTS.md
├── .opencode/memory-bank/     # память агента между сессиями
├── backend/                   # FastAPI, Alembic, тесты
├── frontend/                  # React (следующий этап)
├── docs/                      # проектная документация (MD + DOCX)
├── deploy/alwaysdata/         # инструкции и конфигурация хостинга
└── scripts/                   # генерация документации и служебные скрипты
```

## Быстрый старт backend

1. Установить Python 3.12+; PostgreSQL можно не устанавливать локально —
   пилотная БД уже развёрнута на Alwaysdata.
2. Создать виртуальное окружение: `python -m venv .venv`.
3. Активировать: `.venv\Scripts\Activate.ps1`.
4. Установить зависимости: `pip install -r backend/requirements.txt`.
5. Заполнить `.env` (рабочий `.env` пилота уже создан и исключён из Git).
6. Применить миграции: `cd backend; $env:PYTHONPATH='.'; python -m alembic upgrade head`.
7. Создать пилотные данные: `python -m app.db.seed`.
8. Запустить API: `uvicorn app.main:app --reload --port 8000`.
9. Открыть `http://localhost:8000/docs`.

Подробнее — в [backend/README.md](backend/README.md) и
[документе развёртывания](docs/07-operations/01-razvertyvanie-i-ekspluataciya.md).

## Документация

- [Реестр документов](docs/00-register/01-register-dokumentacii.md)
- [Концепция](docs/01-concept/01-koncepciya.md)
- [Техническое задание](docs/02-tz/01-tehnicheskoe-zadanie.md)
- [Функции по ролям](docs/02-tz/02-funkcionalnye-trebovaniya-po-rolyam.md)
- [Карта миграции](docs/02-tz/05-karta-migracii.md)
- [Архитектура](docs/03-architecture/01-arhitektura.md)
- [API пилотного контура](docs/03-architecture/03-api.md)
- [Модель данных](docs/04-data/01-model-dannyh.md)
- [Безопасность](docs/05-security/01-koncepciya-ib.md)
- [План разработки](docs/08-roadmap/01-plan-razrabotki.md)
- [Нормативные документы](docs/09-normative/01-reestr-normativnyh-dokumentov.md)
- [Отчёт о завершении этапа 1](docs/10-reporting/06-otchet-o-zavershenii-etapa-1.md)

## Правила работы

Основные правила для разработчика и AI-агента — в [AGENTS.md](AGENTS.md).
Перед каждой сессией OpenCode читает `.opencode/memory-bank/activeContext.md`.
Старый проект `C:\Users\adamrv\Documents\edu-math` не изменяется и не
останавливается.
