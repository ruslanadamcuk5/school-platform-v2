# Alwaysdata: пилотный контур

## 1. Фактически созданные ресурсы

| Ресурс | Значение |
|---|---|
| GitHub | `ruslanadamcuk5/school-platform-v2` (private) |
| Сайт (пилот) | `https://school-platform-v2.185.31.40.24.nip.io` |
| SSL | Let's Encrypt, до 2027-01-25, Force HTTPS включён |
| Тип сайта | **User program (Uvicorn)** |
| Рабочая директория | `/home/virusadk/school-platform-v2/backend` |
| Команда | `uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"` |
| Venv | `/home/virusadk/.virtualenvs/school-platform` |
| PostgreSQL host | `postgresql-virusadk.alwaysdata.net` |
| PostgreSQL port | `5432` |
| База | `virusadk_school_platform` |
| Пользователь БД | `virusadk` |
| SSH | `ssh-virusadk.alwaysdata.net`, пользователь `virusadk` |
| SSH key | `uchus-deploy` (`id_ed25519_uchus`) |
| Старый сайт | `https://virusadk.alwaysdata.net` — **не изменять** |

Пароль БД и `ADMIN_PASSWORD` хранятся только в локальном `.env`, в
`backend/.env` на сервере и в панели Alwaysdata. В репозиторий и документацию
они не записываются.

### Почему адрес `nip.io`

На бесплатном аккаунте Alwaysdata нельзя занять произвольное имя вида
`school-platform-v2.alwaysdata.net`: домен `alwaysdata.net` принадлежит
хостингу. Поэтому для пилота используется технический адрес
`school-platform-v2.185.31.40.24.nip.io`, который указывает на IP аккаунта.
Для промышленного контура нужен собственный домен, например
`school.example.by`, с A-записью на `185.31.40.24`.

## 2. PostgreSQL

Созданы схемы:

```text
iam, org, lms, assessment, journal, communication,
safety, documents, analytics, ai, audit, system
```

Подключены расширения:

```text
citext, pgcrypto, pg_trgm, vector, unaccent, uuid-ossp
```

Применена миграция:

```text
0002_groups_permissions_services (head)
```

Созданы таблицы:

```text
iam.users, iam.refresh_tokens,
org.schools, org.classes, org.class_memberships,
audit.events
```

Пилотные данные: школа `pilot-school`, классы 1–11, супер-администратор
`admin` (пароль — `ADMIN_PASSWORD` в `.env`).

## 3. Сайт

Сайт #1092629 работает как **User program**. Настройки в панели:

| Поле | Значение |
|---|---|
| Type | User program |
| Command | `/home/virusadk/.virtualenvs/school-platform/bin/uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"` |
| Working directory | `school-platform-v2/backend` |
| Environment | `PYTHONPATH=. PYTHONUNBUFFERED=1` |
| Cache | **выключен** (API не кэшируется) |
| Force HTTPS | включён |
| WAF | basic |

Важно: поле **Working directory** в панели Alwaysdata задаётся относительно
`/home/virusadk`. Если указать абсолютный путь, панель удваивает префикс
(`/home/virusadk/home/virusadk/...`) и процесс не стартует.

Проверка:

- `GET /health` → 200, `database: ok`.
- `GET /docs` → Swagger UI.
- `GET /openapi.json` → OpenAPI 3.1.
- `GET /robots.txt` → `Disallow: /`.
- HTTP → 301 HTTPS.
- Заголовки: `X-Robots-Tag: noindex`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, HSTS.

## 4. Переменные окружения

Локально: `.env` в корне проекта (не коммитится).
На сервере: `backend/.env` (не коммитится).

Минимально нужны:

```text
DATABASE_URL=postgresql+asyncpg://virusadk:***@postgresql-virusadk.alwaysdata.net:5432/virusadk_school_platform
SECRET_KEY=...
JWT_PRIVATE_KEY_PATH=./secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./secrets/jwt_public.pem
ADMIN_LOGIN=admin
ADMIN_PASSWORD=...
SEED_SCHOOL_CODE=pilot-school
CORS_ORIGINS=https://school-platform-v2.185.31.40.24.nip.io
```

Ключи JWT лежат в `backend/secrets/` на сервере с правами `600` на приватный
ключ. В Git не попадают.

## 5. Деплой

Текущий способ — архивы backend и frontend по SSH (GitHub-ключ Alwaysdata
не добавлялся в репозиторий):

```powershell
$tar = "$env:TEMP\opencode\school-platform-backend.tgz"
tar.exe -czf $tar --exclude='__pycache__' --exclude='.ruff_cache' `
  --exclude='*.pyc' --exclude='.pytest_cache' `
  -C backend .env secrets app alembic alembic.ini requirements.txt README.md pytest.ini tests
scp -i C:\Users\adamrv\.ssh\id_ed25519_uchus $tar `
  virusadk@ssh-virusadk.alwaysdata.net:/home/virusadk/school-platform-v2/backend.tgz
ssh -i C:\Users\adamrv\.ssh\id_ed25519_uchus `
  virusadk@ssh-virusadk.alwaysdata.net `
  "cd /home/virusadk/school-platform-v2 && tar -xzf backend.tgz -C backend"
```

Публикация веб-клиента:

```powershell
$dist = "$env:TEMP\opencode\school-platform-frontend.tgz"
tar.exe -czf $dist -C frontend dist
scp -i C:\Users\adamrv\.ssh\id_ed25519_uchus $dist `
  virusadk@ssh-virusadk.alwaysdata.net:/home/virusadk/school-platform-v2/frontend.tgz
ssh -i C:\Users\adamrv\.ssh\id_ed25519_uchus `
  virusadk@ssh-virusadk.alwaysdata.net `
  "cd /home/virusadk/school-platform-v2 && mkdir -p frontend && tar -xzf frontend.tgz -C frontend"
```

FastAPI отдаёт SPA, если на сервере существует
`frontend/dist/index.html`. API и Swagger не затрагиваются.

После обновления кода перезапустить процесс сайта:

1. Открыть **Advanced → Processes**.
2. Найти процесс `uvicorn app.main:app`.
3. Нажать **Terminate** (не Kill).
4. Открыть сайт — Alwaysdata запустит новый процесс.

Установка зависимостей:

```bash
/home/virusadk/.virtualenvs/school-platform/bin/pip install --no-cache-dir \
  -r /home/virusadk/school-platform-v2/backend/requirements.txt
```

Миграции и seed:

```bash
cd /home/virusadk/school-platform-v2/backend
export PYTHONPATH=.
/home/virusadk/.virtualenvs/school-platform/bin/python -m alembic upgrade head
/home/virusadk/.virtualenvs/school-platform/bin/python -m app.db.seed
```

## 6. Проверка после деплоя

```bash
curl -i https://school-platform-v2.185.31.40.24.nip.io/health
curl -i https://school-platform-v2.185.31.40.24.nip.io/robots.txt
curl -i https://school-platform-v2.185.31.40.24.nip.io/openapi.json
curl -i https://virusadk.alwaysdata.net/healthz
```

Ожидаемо: новый сайт — 200, старый сайт — 200, HTTP — 301.

## 7. Ограничения

- Это пилотный контур, не промышленный.
- Для аттестации и реальных ПДн нужен согласованный ЦОД.
- Внешние AI-сервисы включать только после оценки рисков.
- Домен `nip.io` — технический; для сдачи проекта нужен собственный домен.
- Redis, фоновые задачи и rate limiting в пилоте не подключены.
- Пароль супер-администратора сменить после передачи заказчику.
