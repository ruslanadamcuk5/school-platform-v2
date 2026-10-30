# Развёртывание и эксплуатация

| Параметр | Значение |
|---|---|
| Код документа | ШК-07-01 |
| Версия | 0.4 |
| Статус | Рабочий |
| Дата | 30.10.2026 |

## 1. Среды
| Среда | Назначение | Домен |
|---|---|---|
| Local | Разработка | localhost |
| Dev | Интеграция | dev.* |
| Stage | Приёмка | stage.* |
| Pilot | Опытная эксплуатация | pilot.* |
| Prod | Промышленная | *.by |

## 2. Локальная разработка
### 2.1. Требования
- Python 3.12+.
- PostgreSQL 16+ (локально или managed).
- Redis 7+.
- Node.js 20+ (для frontend и MCP); при отсутствии используется переносимый
  дистрибутив в `.tools/` (не коммитится).
- Docker Desktop (рекомендуется).
- Git.

### 2.2. Запуск
```powershell
cd C:\Users\adamrv\Documents\school-platform-v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
copy .env.example .env
# заполнить DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD, JWT_*
cd backend
$env:PYTHONPATH='.'
python -m alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

Если Docker недоступен, используется managed PostgreSQL (пилотный контур
Alwaysdata) или локальный PostgreSQL, установленный отдельно. В текущей
рабочей среде Docker, Node.js и локальный PostgreSQL отсутствуют; пилот
работает на managed PostgreSQL.
Frontend:
```powershell
cd frontend
npm install
npm run dev

Если системного Node.js нет, используйте `.tools/node-v22.14.0-win-x64`,
добавив его в `PATH`. Обязательные проверки перед коммитом:
`npm run typecheck` и `npm run build`.
```

### 2.3. Проверка
- `GET /health` → 200.
- `GET /docs` → OpenAPI.
- Подключение к БД и Redis.
- Миграции применены.

## 3. Alwaysdata (пилот)
### 3.1. Сайт
- Новый профиль: `school-platform-v2`.
- Адрес пилота: `https://school-platform-v2.alwaysdata.net`.
- SSH: `school-platform-v2@ssh-school-platform-v2.alwaysdata.net`,
  ключ `id_ed25519_school_platform`.
- Каталог проекта: `/home/school-platform-v2/school-platform-v2`.
- Backend: `/home/school-platform-v2/school-platform-v2/backend`.
- Frontend dist: `/home/school-platform-v2/school-platform-v2/frontend/dist`.
- Venv: `/home/school-platform-v2/.virtualenvs/school-platform`.
- Текущий тип сайта: **Python WSGI (uWSGI 2.0.31)**.
- uWSGI загружает `backend/__init__.py` — копию
  `deploy/alwaysdata/wsgi_entry.py`. Адаптер `a2wsgi` оборачивает FastAPI в
  WSGI и добавляет `site-packages` проекта в `sys.path`.
- Альтернатива — переключить сайт на **User program** и использовать Uvicorn:
  `/home/school-platform-v2/.virtualenvs/school-platform/bin/uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"`.
  Рабочая директория в панели: `school-platform-v2/backend` (относительно
  `/home/school-platform-v2`).
- Переменные: `PYTHONPATH=. PYTHONUNBUFFERED=1`.
- Кэш сайта отключён; WAF — basic; `Force HTTPS` включён.
- Сайт не затрагивает `virusadk.alwaysdata.net`.
- `robots.txt` закрывает пилот от индексации; добавлены security headers
  (`X-Robots-Tag`, `X-Content-Type-Options`, `X-Frame-Options`, HSTS).

### 3.2. PostgreSQL
- Используется существующая БД: `virusadk_school_platform`.
- Хост: `postgresql-virusadk.alwaysdata.net:5432`.
- Новый хост успешно подключается к ней; данные и пользователи сохранены.
- Пароль хранится в `.env` и менеджере секретов.
- Созданы схемы: `iam`, `org`, `lms`, `assessment`, `journal`,
  `communication`, `safety`, `documents`, `analytics`, `ai`, `audit`,
  `system`.
- Подключены расширения: `citext`, `pgcrypto`, `pg_trgm`, `vector`,
  `unaccent`, `uuid-ossp`.
- Миграция: `0002_groups_permissions_services (head)`.
- Доступ только с IP/хостов приложения, если возможно.
- Ежедневный дамп и проверка восстановления.

### 3.3. Переменные окружения
Задаются в `.env` на сервере (не коммитится):
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `JWT_*`
- `AI_*`
- `S3_*`
- `CORS_ORIGINS` — `https://school-platform-v2.alwaysdata.net`

### 3.4. Деплой
1. Подключиться по SSH ключом `id_ed25519_school_platform`.
2. Перейти в `/home/school-platform-v2/school-platform-v2`.
3. Доставить backend-архив без `.env` и `secrets/`.
4. Распаковать в `backend/`.
5. Скопировать `deploy/alwaysdata/wsgi_entry.py` в `backend/__init__.py`.
6. Установить зависимости:
   `/home/school-platform-v2/.virtualenvs/school-platform/bin/pip install --no-cache-dir -r backend/requirements.txt`
   и `deploy/alwaysdata/requirements-wsgi.txt`.
7. Выполнить `PYTHONPATH=. python -m alembic upgrade head` в `backend/`.
8. Выполнить `python -m app.db.seed` только при первом развёртывании пустой БД.
9. Перезапустить процесс сайта: **Advanced → Processes** (uWSGI). Если процесс
   упал, новый стартует при следующем HTTP-запросе.
10. Проверить `/health`, `/`, `/groups`, `/docs`, `/robots.txt`, старый сайт.

### 3.4.1. Публикация веб-клиента
1. Собрать клиент локально: `npm run build` в `frontend/`.
2. Доставить `frontend/dist` на пилот в
   `/home/school-platform-v2/school-platform-v2/frontend/dist`.
3. FastAPI автоматически раздаёт `index.html` на `/` и клиентские
   маршруты, а `/assets/*` — из `frontend/dist/assets`.
4. API, `/health`, `/docs`, `/openapi.json` и `/robots.txt` сохраняют
   прежнее поведение.
5. Если `frontend/dist` отсутствует, `/` возвращает JSON-описание
   сервиса, поэтому backend-only развёртывание остаётся совместимым.

Текущий архив backend и frontend собирается локально и копируется через `scp`.
Для регулярного деплоя нужно создать отдельный read-only deploy key и перейти
на `git pull`.

### 3.5. Ограничения пилота
Alwaysdata подходит для пилота и демонстрации, но не заменяет
аттестованный ЦОД для промышленной эксплуатации. Для промышленного контура
требуется отдельная инфраструктура на территории Республики Беларусь.
В пилоте нет Redis, фоновых задач, rate limiting и WAF уровня приложения;
внешние AI-сервисы выключены. Пароль супер-администратора хранится в
`backend/.env` и должен быть сменён после передачи заказчику.

## 4. Промышленная инфраструктура
- Kubernetes или отказоустойчивый кластер ВМ.
- PostgreSQL с репликацией.
- Redis Cluster.
- S3-совместимое хранилище.
- WAF, балансировщик, CDN.
- Мониторинг и логирование.
- Резервный ЦОД.
- Сертифицированные СЗИ при необходимости.

## 5. CI/CD
### 5.1. Pipeline
1. Линтеры и форматирование.
2. Юнит-тесты.
3. Интеграционные тесты.
4. Сборка образов.
5. Сканирование зависимостей и образов.
6. Миграции на Stage.
7. E2E и нагрузочные (по расписанию).
8. Деплой на Stage/Prod с подтверждением.

### 5.2. Ветки
- `main` — стабильная.
- `develop` — интеграция.
- `feature/*` — задачи.
- `hotfix/*` — срочные исправления.

### 5.3. Версионирование
SemVer: `MAJOR.MINOR.PATCH`. Мобильные приложения — отдельные versionCode/build.

## 6. Резервное копирование
- PostgreSQL: ежедневно, WAL для PITR.
- Файлы: ежедневно, версионирование.
- Конфигурации: при каждом изменении.
- Хранение: 30 дней минимум, для критичных — больше.
- Проверка восстановления: ежемесячно.

## 7. Мониторинг
- Доступность API и сайта.
- Latency p50/p95/p99.
- Ошибки 4xx/5xx.
- Очереди и их длина.
- БД: соединения, медленные запросы, репликация.
- AI: ошибки, задержки, расход токенов.
- Безопасность: подозрительные входы, аномалии.
- Алерты в дежурный канал.

## 8. Логирование
- Structured JSON logs.
- `request_id` во всех сервисах.
- Запрет ПДн и секретов в логах.
- Централизованное хранение.
- Срок хранения по политике.

## 9. Обновления
- Регулярные окна обслуживания.
- Уведомление пользователей.
- Canary/blue-green для критичных сервисов.
- План отката.
- Миграции — обратно совместимые.

## 10. Инциденты
- Дежурство и эскалация.
- Классификация.
- Коммуникация с пользователями.
- Постмортем без поиска виновных.
- Корректирующие задачи.

## 11. Эксплуатационная документация
- Runbook дежурного.
- Инструкция по восстановлению.
- Инструкция по миграциям.
- Инструкция по секретам.
- Контакты ответственных.
- Схема инфраструктуры.

## 12. Чек-лист запуска
- [ ] Секреты заданы.
- [ ] БД создана и мигрирована.
- [ ] Резервное копирование настроено.
- [ ] Мониторинг и алерты.
- [ ] HTTPS и домен.
- [ ] WAF и rate limiting.
- [ ] Тестовые пользователи удалены.
- [ ] Демо-данные не попали в Prod.
- [ ] Документация обновлена.
- [ ] Поддержка уведомлена.
