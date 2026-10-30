# ЕООП «Школьник» — school-platform-v2

Новая версия единой общеобразовательной обучающей платформы для Республики
Беларусь. Проект создаётся как преемник работающего Flask/SQLite-приложения:
существующий функционал переносится поэтапно, без остановки текущего сервиса.

## Текущий статус

**Этап 0 — инициализация завершена.**
**Этап 1 — анализ и пилотный backend завершён.**
**Этап 2 — ядро, LMS, тесты, журнал и библиотека.**
**Этап 2.5 — микросервисная модель и групповые права.**

Реализован FastAPI-backend с health-check, OpenAPI, SQLAlchemy 2.0 async,
Alembic, JWT, мультитенантностью по `school_id`, доменами LMS, assessment,
journal и library. Добавлены реестр микросервисов, включение/отключение
функционала по областям иерархии и групповая модель прав (GBAC): права
назначаются группам, а не пользователям.

### Пилотные ресурсы

| Ресурс | Адрес / значение |
|---|---|
| GitHub | `https://github.com/ruslanadamcuk5/school-platform-v2` (private) |
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

### Ядро и доступ
- `GET /health`, `GET /api/v1/health` — проверка API и БД.
- `GET /api/v1/meta` — версия, языки, feature flags.
- `POST /api/v1/auth/login`, `/refresh`, `/logout`, `GET /auth/me`.
- `GET /api/v1/org/schools`, `/org/classes` — школы и классы с tenant-проверкой.
- `GET /api/v1/admin/stats`, `/admin/users`, `/admin/audit`.
- `POST /api/v1/admin/users` — создание пользователя школы.

### Группы и права
- `GET/POST /api/v1/groups`, `GET/PATCH/DELETE /groups/{id}`.
- `POST/DELETE /groups/{id}/members` — управление составом группы.
- `PUT/DELETE /groups/{id}/permissions/{code}` — выдача и снятие прав.
- `GET /api/v1/groups/permissions` — каталог прав.
- `GET /api/v1/me/permissions` — действующие права пользователя.
- 5 уровней групп: страна → область → город → школа → класс.
- Наследование по явному родителю и организационным предкам категории.
- При равной глубине `deny` побеждает `allow`.

### Микросервисы и функционал
- `GET /api/v1/services` — каталог 14 сервисов.
- `PUT /api/v1/services/{code}/activation` — включение/отключение для области.
- `GET /api/v1/me/services` — сервисы, доступные пользователю (для навигации).
- `app/service_app.py` — запуск любого сервиса отдельным процессом.
- Домены: `lms`, `assessment`, `journal`, `library`.
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

Запуск отдельного сервиса:

```powershell
$env:SERVICE_CODE='library'
uvicorn app.service_app:create_service_app --factory --port 8101
```

Подробнее — в [backend/README.md](backend/README.md) и
[документе развёртывания](docs/07-operations/01-razvertyvanie-i-ekspluataciya.md).

## Документация

- [Реестр документов](docs/00-register/01-register-dokumentacii.md)
- [Концепция](docs/01-concept/01-koncepciya.md)
- [Техническое задание](docs/02-tz/01-tehnicheskoe-zadanie.md)
- [Функции по ролям](docs/02-tz/02-funkcionalnye-trebovaniya-po-rolyam.md)
- [Карта миграции](docs/02-tz/05-karta-migracii.md)
- [Архитектура](docs/03-architecture/01-arhitektura.md)
- [Микросервисы](docs/03-architecture/04-mikroservisy.md)
- [Группы и права](docs/03-architecture/05-gruppy-i-prava.md)
- [API пилотного контура](docs/03-architecture/03-api.md)
- [Модель данных](docs/04-data/01-model-dannyh.md)
- [Модель групп и сервисов](docs/04-data/02-model-grupp-prav-i-servisov.md)
- [Безопасность](docs/05-security/01-koncepciya-ib.md)
- [План разработки](docs/08-roadmap/01-plan-razrabotki.md)
- [Нормативные документы](docs/09-normative/01-reestr-normativnyh-dokumentov.md)
- [Отчёт о завершении этапа 1](docs/10-reporting/06-otchet-o-zavershenii-etapa-1.md)
- [Отчёт о тестировании групп, прав и сервисов](docs/10-reporting/10-otchet-o-testirovanii-groups-services.md)

## Правила работы

Основные правила для разработчика и AI-агента — в [AGENTS.md](AGENTS.md).
Перед каждой сессией OpenCode читает `.opencode/memory-bank/activeContext.md`.
Старый проект `C:\Users\adamrv\Documents\edu-math` не изменяется и не
останавливается.
