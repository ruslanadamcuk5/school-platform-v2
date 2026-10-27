# Alwaysdata: пилотный контур

## 1. Фактически созданные ресурсы

| Ресурс | Значение |
|---|---|
| GitHub | `newvirusadk-cmd/school-platform-v2` (private) |
| Сайт (пилот) | `http://school-platform-v2.185.31.40.24.nip.io` |
| Тип сайта | Static files (временная страница-заглушка) |
| Корень сайта | `/home/virusadk/school-platform-v2/public` |
| PostgreSQL host | `postgresql-virusadk.alwaysdata.net` |
| PostgreSQL port | `5432` |
| База | `virusadk_school_platform` |
| Пользователь БД | `virusadk` |
| SSH | `ssh-virusadk.alwaysdata.net`, пользователь `virusadk` |
| SSH key | `uchus-deploy` (`id_ed25519_uchus`) |

Пароль БД хранится только в локальном `.env` и в панели Alwaysdata.
В репозиторий и документацию он не записывается.

### Почему адрес `nip.io`

На бесплатном аккаунте Alwaysdata нельзя занять произвольное имя вида
`school-platform-v2.alwaysdata.net`: домен `alwaysdata.net` принадлежит
хостингу. Поэтому для пилота используется технический адрес
`school-platform-v2.185.31.40.24.nip.io`, который указывает на IP аккаунта.
Для промышленного контура нужен собственный домен, например
`school.example.by`, с A-записью на `185.31.40.24`.

## 2. Что уже настроено в PostgreSQL

Созданы схемы:

```text
iam, org, lms, assessment, journal, communication,
safety, documents, analytics, ai, audit, system
```

Подключены расширения:

```text
citext, pgcrypto, pg_trgm, vector, unaccent, uuid-ossp
```

Проверка подключения:

```bash
python -c "import asyncio, asyncpg; ..."
```

или после установки зависимостей:

```bash
cd backend
alembic upgrade head
```

## 3. Сайт

Сейчас сайт работает как **Static files** и отдаёт страницу-заглушку
`deploy/alwaysdata/public/index.html`.

После появления FastAPI backend сайт нужно переключить на **User program**:

```bash
uvicorn app.main:app --host $IP --port $PORT --proxy-headers
```

Рабочая директория:

```text
/home/virusadk/school-platform-v2/backend
```

Команда должна запускаться из виртуального окружения:

```text
/home/virusadk/.virtualenvs/school-platform/bin/activate
```

## 4. Переменные окружения

Локально: `.env` в корне проекта (не коммитится).
На сервере: `.env` в каталоге backend или переменные в панели Alwaysdata.

Минимально нужны:

```text
DATABASE_URL=postgresql+asyncpg://virusadk:***@postgresql-virusadk.alwaysdata.net:5432/virusadk_school_platform
SECRET_KEY=...
JWT_PRIVATE_KEY_PATH=./secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./secrets/jwt_public.pem
```

## 5. Деплой

```bash
ssh virusadk@ssh-virusadk.alwaysdata.net
cd /home/virusadk/school-platform-v2
git pull
source /home/virusadk/.virtualenvs/school-platform/bin/activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
```

Затем перезапустить процесс сайта в панели Alwaysdata.

## 6. Проверка

- `GET /health` → 200.
- `GET /docs` → OpenAPI.
- Логи процесса без ошибок.
- Подключение к БД и Redis.
- HTTPS-сертификат выпущен и включён `Force HTTPS`.

## 7. Ограничения

- Это пилотный контур, не промышленный.
- Для аттестации и реальных ПДн нужен согласованный ЦОД.
- Внешние AI-сервисы включать только после оценки рисков.
- Домен `nip.io` — технический; для сдачи проекта нужен собственный домен.
- Статическая заглушка не является прикладной системой.
