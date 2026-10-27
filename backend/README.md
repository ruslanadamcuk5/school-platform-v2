# Backend (FastAPI)

Пилотный backend платформы «Школьник». Реализованы:

- FastAPI + OpenAPI (`/docs`, `/redoc`, `/openapi.json`);
- health-check с проверкой PostgreSQL (`/health`, `/api/v1/health`);
- SQLAlchemy 2.0 async + asyncpg;
- Alembic-миграции;
- JWT access-токены (RS256) и opaque refresh-токены с хранением только SHA-256;
- RBAC (`superadmin`, `admin`, `methodologist`, `teacher`, `student`, `parent`,
  `psychologist`, `secretary`);
- мультитенантность по `school_id` с проверкой на уровне API;
- журнал аудита входов, токенов и административных действий;
- восстановление пароля через bcrypt (12 rounds);
- сид пилотной школы, классов 1–11 и супер-администратора.

## Структура

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py            # JWT, роли, tenant scope
│   │   └── v1/
│   │       ├── admin.py       # пользователи, статистика, аудит
│   │       ├── auth.py        # login/refresh/logout/me
│   │       ├── org.py         # школы и классы
│   │       ├── system.py      # health/meta
│   │       └── router.py
│   ├── core/
│   │   ├── config.py          # pydantic-settings
│   │   └── security.py        # bcrypt, JWT, refresh tokens
│   ├── db/
│   │   ├── base.py
│   │   ├── seed.py
│   │   └── session.py
│   ├── models/                # iam, org, audit
│   ├── schemas/               # Pydantic v2
│   ├── services/              # auth, audit
│   └── main.py
├── alembic/
│   ├── env.py
│   └── versions/0001_initial.py
├── tests/
├── alembic.ini
├── pytest.ini
└── requirements.txt
```

## Локальный запуск

```powershell
cd C:\Users\adamrv\Documents\school-platform-v2
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
$env:PYTHONPATH='.'
python -m alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

Проверки:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/meta
Invoke-WebRequest http://localhost:8000/docs
python -m pytest
python -m ruff check app alembic tests
```

## Переменные окружения

Корневой `.env` (локально) или `backend/.env` (на сервере). Минимально:

```text
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
SECRET_KEY=...
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=./secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./secrets/jwt_public.pem
ADMIN_LOGIN=admin
ADMIN_PASSWORD=...
SEED_SCHOOL_CODE=pilot-school
SEED_SCHOOL_NAME=Пилотная школа «Школьник»
SEED_ACADEMIC_YEAR=2026/2027
CORS_ORIGINS=https://school-platform-v2.185.31.40.24.nip.io
```

`.env`, `secrets/` и ключи не коммитятся.

## API (пилот)

| Метод | Путь | Доступ |
|---|---|---|
| GET | `/health` | публично |
| GET | `/api/v1/health` | публично |
| GET | `/api/v1/meta` | публично |
| POST | `/api/v1/auth/login` | публично |
| POST | `/api/v1/auth/refresh` | публично (refresh token) |
| POST | `/api/v1/auth/logout` | access token |
| GET | `/api/v1/auth/me` | access token |
| GET | `/api/v1/org/schools` | авторизованный |
| GET | `/api/v1/org/schools/{id}` | своя школа; superadmin — любая |
| GET | `/api/v1/org/classes` | своя школа; superadmin — `school_id` |
| GET | `/api/v1/org/classes/{id}` | своя школа |
| GET | `/api/v1/admin/stats` | admin/superadmin |
| GET | `/api/v1/admin/users` | admin/superadmin |
| POST | `/api/v1/admin/users` | admin/superadmin |
| GET | `/api/v1/admin/audit` | admin/superadmin |

Для superadmin эндпоинты школы требуют `?school_id=<uuid>`. Для остальных
ролей `school_id` берётся из токена, а попытка передать чужой `school_id`
возвращает `403`.

### Пример входа

```powershell
$body = @{ login = 'admin'; password = (Select-String -Path ..\.env -Pattern '^ADMIN_PASSWORD=').Line.Split('=')[1] } | ConvertTo-Json
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login -ContentType 'application/json' -Body $body
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod http://localhost:8000/api/v1/auth/me -Headers $headers
```

## Тесты

- `tests/test_security.py` — bcrypt, JWT, refresh-токены.
- `tests/test_openapi.py` — наличие ключевых маршрутов и Bearer-схемы.

Интеграционный smoke-тест с реальной БД выполнялся отдельно при развёртывании:
вход, `/me`, школы, классы, статистика, запрет cross-tenant, запрет RBAC,
ротация refresh-токена и отзыв при logout.

## Миграции

```powershell
python -m alembic current
python -m alembic history
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade -1
```

`alembic check` должен сообщать `No new upgrade operations detected`: модель и
фактическая схема PostgreSQL синхронизированы.

Все таблицы создаются в схемах `iam`, `org`, `audit`.
