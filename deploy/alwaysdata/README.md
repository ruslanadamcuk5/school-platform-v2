# Alwaysdata: пилотный контур

## 1. Фактические ресурсы

| Ресурс | Значение |
|---|---|
| GitHub | `https://github.com/ruslanadamcuk5/school-platform-v2` (private) |
| Пилотный сайт | `https://school-platform-v2.alwaysdata.net` |
| Аккаунт Alwaysdata | `school-platform-v2` |
| SSH-хост | `ssh-school-platform-v2.alwaysdata.net` |
| SSH-пользователь | `school-platform-v2` |
| SSH-ключ | `id_ed25519_school_platform` (локально, в Git не попадает) |
| Домашний каталог | `/home/school-platform-v2` |
| Каталог проекта | `/home/school-platform-v2/school-platform-v2` |
| Backend | `/home/school-platform-v2/school-platform-v2/backend` |
| Frontend dist | `/home/school-platform-v2/school-platform-v2/frontend/dist` |
| Venv | `/home/school-platform-v2/.virtualenvs/school-platform` |
| Тип сайта | **Python WSGI (uWSGI 2.0.31)** |
| PostgreSQL host | `postgresql-virusadk.alwaysdata.net:5432` |
| База | `virusadk_school_platform` |
| Старый сайт | `https://virusadk.alwaysdata.net` — **не изменять** |

Пароль БД и `ADMIN_PASSWORD` хранятся только в локальном `.env`, в
`backend/.env` на сервере и в панели Alwaysdata. В репозиторий и документацию
они не записываются.

## 2. Почему WSGI, а не Uvicorn

Новый профиль был создан как **Python WSGI**-сайт. Alwaysdata передаёт
приложение в uWSGI, а проект построен на ASGI/FastAPI. Для совместимости
используется адаптер `a2wsgi`:

- `deploy/alwaysdata/wsgi_entry.py` копируется на сервер как
  `backend/__init__.py`; на текущем сервере используется эквивалентная версия
  с явным путём к `site-packages`, а шаблон находит venv автоматически;
- файл добавляет `site-packages` проекта в `sys.path`;
- FastAPI оборачивается в `a2wsgi.ASGIMiddleware`;
- uWSGI загружает `backend/__init__.py`, потому что поле `wsgi-file` указывает
  на каталог `backend/`.

Установка адаптера:

```bash
/home/school-platform-v2/.virtualenvs/school-platform/bin/pip install \
  --no-cache-dir -r /home/school-platform-v2/school-platform-v2/deploy/alwaysdata/requirements-wsgi.txt
```

### 2.1. Альтернатива: User program (Uvicorn)

Если сайт переключить на **User program**, адаптер не нужен. Настройки:

| Поле | Значение |
|---|---|
| Command | `/home/school-platform-v2/.virtualenvs/school-platform/bin/uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"` |
| Working directory | `school-platform-v2/backend` |
| Environment | `PYTHONPATH=. PYTHONUNBUFFERED=1` |

Рабочая директория задаётся **относительно** `/home/school-platform-v2`.
Абсолютный путь панель может удвоить, и процесс не стартует.

## 3. PostgreSQL

Пилот использует существующую базу `virusadk_school_platform` на старом
аккаунте. Новый хост успешно подключается к ней, поэтому данные и пользователи
сохранены.

- Миграция: `0002_groups_permissions_services (head)`.
- Схемы: `iam`, `org`, `lms`, `assessment`, `journal`, `communication`,
  `safety`, `documents`, `analytics`, `ai`, `audit`, `system`.
- Расширения: `citext`, `pgcrypto`, `pg_trgm`, `vector`, `unaccent`,
  `uuid-ossp`.
- Проверка подключения с сервера:

```bash
cd /home/school-platform-v2/school-platform-v2/backend
PYTHONPATH=. /home/school-platform-v2/.virtualenvs/school-platform/bin/python \
  -m alembic current
```

Команда должна показать `0002_groups_permissions_services (head)`.

Если позже понадобится отдельная база нового профиля, её нужно создать в
панели, обновить `DATABASE_URL` в `backend/.env`, применить
`alembic upgrade head` и выполнить seed только для пустой базы.

## 4. Настройки сайта

| Поле | Значение |
|---|---|
| Type | **Python WSGI** |
| Working directory | `school-platform-v2/backend` |
| WSGI application | каталог `backend/` (`backend/__init__.py`) |
| Environment | `PYTHONPATH=. PYTHONUNBUFFERED=1` |
| Cache | выключен |
| Force HTTPS | включён |
| WAF | basic |

`backend/__init__.py` — это эквивалент `deploy/alwaysdata/wsgi_entry.py`. При
пересоздании сайта шаблон нужно скопировать заново.

После изменения кода перезапустить процесс можно в
**Advanced → Processes**: остановить/перезапустить процесс uWSGI. Если процесс
упал, новый стартует при следующем HTTP-запросе.

## 5. Деплой

### 5.1. Backend

```powershell
$tar = "$env:TEMP\opencode\school-platform-backend.tgz"
tar.exe -czf $tar --exclude='__pycache__' --exclude='.ruff_cache' `
  --exclude='*.pyc' --exclude='.pytest_cache' `
  -C backend app alembic alembic.ini requirements.txt README.md pytest.ini tests
scp -i C:\Users\adamrv\.ssh\id_ed25519_school_platform $tar `
  school-platform-v2@ssh-school-platform-v2.alwaysdata.net:/home/school-platform-v2/school-platform-v2/backend.tgz
ssh -i C:\Users\adamrv\.ssh\id_ed25519_school_platform `
  school-platform-v2@ssh-school-platform-v2.alwaysdata.net `
  "cd /home/school-platform-v2/school-platform-v2 && tar -xzf backend.tgz -C backend && rm backend.tgz"
```

`.env` и `secrets/` в архив не включаются, чтобы не перезаписывать серверные
секреты.

### 5.2. Frontend

```powershell
$dist = "$env:TEMP\opencode\school-platform-frontend.tgz"
tar.exe -czf $dist -C frontend dist
scp -i C:\Users\adamrv\.ssh\id_ed25519_school_platform $dist `
  school-platform-v2@ssh-school-platform-v2.alwaysdata.net:/home/school-platform-v2/school-platform-v2/frontend.tgz
ssh -i C:\Users\adamrv\.ssh\id_ed25519_school_platform `
  school-platform-v2@ssh-school-platform-v2.alwaysdata.net `
  "cd /home/school-platform-v2/school-platform-v2 && mkdir -p frontend && tar -xzf frontend.tgz -C frontend && rm frontend.tgz"
```

FastAPI автоматически раздаёт `frontend/dist`: `/` и клиентские маршруты
отдают `index.html`, `/assets/*` — статику. API, `/health`, `/docs`,
`/openapi.json` и `/robots.txt` не затрагиваются.

### 5.3. WSGI-адаптер и зависимости

```powershell
scp -i C:\Users\adamrv\.ssh\id_ed25519_school_platform `
  deploy\alwaysdata\wsgi_entry.py `
  school-platform-v2@ssh-school-platform-v2.alwaysdata.net:/home/school-platform-v2/school-platform-v2/backend/__init__.py
```

```bash
/home/school-platform-v2/.virtualenvs/school-platform/bin/pip install \
  --no-cache-dir -r /home/school-platform-v2/school-platform-v2/deploy/alwaysdata/requirements-wsgi.txt
```

Права на секреты:

```bash
chmod 600 /home/school-platform-v2/school-platform-v2/backend/.env \
  /home/school-platform-v2/school-platform-v2/backend/secrets/jwt_private.pem
chmod 644 /home/school-platform-v2/school-platform-v2/backend/secrets/jwt_public.pem
```

## 6. Проверка после деплоя

```bash
curl -fsS https://school-platform-v2.alwaysdata.net/health
curl -I  https://school-platform-v2.alwaysdata.net/
curl -I  https://school-platform-v2.alwaysdata.net/groups
curl -I  https://school-platform-v2.alwaysdata.net/docs
curl -I  https://school-platform-v2.alwaysdata.net/robots.txt
curl -I  https://virusadk.alwaysdata.net/healthz
```

Ожидаемо:

- новый сайт: `/health` 200, `/`, `/groups`, `/docs` — 200, `/robots.txt` —
  `Disallow: /`;
- старый сайт `virusadk.alwaysdata.net` — 200, его код и процессы не меняются;
- HTTP → 301 HTTPS;
- security headers: `X-Robots-Tag: noindex`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, HSTS.

Проверка API после входа:

```text
GET /api/v1/me/permissions  -> 73 allow, 0 deny, 1 группа
GET /api/v1/me/services     -> 11
GET /api/v1/groups          -> 30
GET /api/v1/services        -> 14
GET /api/v1/org/schools     -> 1 (pilot-school)
```

## 7. Ограничения

- Это пилотный контур, не промышленный.
- Для аттестации и реальных ПДн нужен согласованный ЦОД.
- Внешние AI-сервисы включать только после оценки рисков.
- Redis, фоновые задачи и rate limiting в пилоте не подключены.
- Пароль супер-администратора сменить после передачи заказчику.
- uWSGI-адаптер — совместимость для текущего типа сайта; целевой production
  runtime — Uvicorn/ASGI.
