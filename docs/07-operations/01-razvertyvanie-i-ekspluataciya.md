# Развёртывание и эксплуатация

| Параметр | Значение |
|---|---|
| Код документа | ШК-07-01 |
| Версия | 0.2 |
| Статус | Рабочий |
| Дата | 27.10.2026 |

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
- Node.js 20+ (для frontend и MCP).
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
```

### 2.3. Проверка
- `GET /health` → 200.
- `GET /docs` → OpenAPI.
- Подключение к БД и Redis.
- Миграции применены.

## 3. Alwaysdata (пилот)
### 3.1. Сайт
- Текущий тип: **User program** (ASGI/Uvicorn).
- Адрес пилота: `https://school-platform-v2.185.31.40.24.nip.io`.
- SSL: Let's Encrypt, срок действия до 2027-01-25, `Force HTTPS` включён.
- Рабочая директория: `/home/virusadk/school-platform-v2/backend`.
- В панели Alwaysdata рабочая директория задаётся **относительно**
  `/home/virusadk`: `school-platform-v2/backend`. Абсолютный путь панель
  удваивает, и процесс не стартует.
- Команда:
  `/home/virusadk/.virtualenvs/school-platform/bin/uvicorn app.main:app --host "$IP" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"`.
- Переменные: `PYTHONPATH=. PYTHONUNBUFFERED=1`.
- Кэш сайта отключён; WAF — basic.
- Сайт отдельный и не затрагивает `virusadk.alwaysdata.net`.
- `robots.txt` закрывает пилот от индексации; добавлены security headers
  (`X-Robots-Tag`, `X-Content-Type-Options`, `X-Frame-Options`, HSTS).

Технический домен `nip.io` выбран потому, что бесплатный аккаунт Alwaysdata
не позволяет занять произвольное имя в зоне `alwaysdata.net`. Для сдачи
пилота и промышленной эксплуатации нужен собственный домен.

### 3.2. PostgreSQL
- Отдельная БД: `virusadk_school_platform`.
- Хост: `postgresql-virusadk.alwaysdata.net:5432`.
- Пользователь: `virusadk`.
- Пароль хранится в `.env` и менеджере секретов.
- Созданы схемы: `iam`, `org`, `lms`, `assessment`, `journal`,
  `communication`, `safety`, `documents`, `analytics`, `ai`, `audit`,
  `system`.
- Подключены расширения: `citext`, `pgcrypto`, `pg_trgm`, `vector`,
  `unaccent`, `uuid-ossp`.
- Доступ только с IP/хостов приложения, если возможно.
- Ежедневный дамп и проверка восстановления.

### 3.3. Переменные окружения
Задаются в панели Alwaysdata или в `.env` на сервере:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `JWT_*`
- `AI_*`
- `S3_*`
- `CORS_ORIGINS`

### 3.4. Деплой
1. Подключиться по SSH.
2. Перейти в `/home/virusadk/school-platform-v2`.
3. Доставить backend-архив (текущий способ) или `git pull` после настройки
   deploy-ключа.
4. Распаковать в `backend/`.
5. Установить зависимости:
   `/home/virusadk/.virtualenvs/school-platform/bin/pip install --no-cache-dir -r backend/requirements.txt`.
6. Выполнить `PYTHONPATH=. python -m alembic upgrade head` в `backend/`.
7. Выполнить `python -m app.db.seed` при первом развёртывании.
8. Перезапустить процесс сайта: **Advanced → Processes → Terminate** для
   `uvicorn app.main:app`; новый процесс стартует при следующем запросе.
9. Проверить `/health`, `/docs`, `/robots.txt`, старый сайт.

Текущий архив backend собирается локально и копируется через `scp`; ключ
Alwaysdata не добавлялся в GitHub-репозиторий. Для регулярного деплоя нужно
создать отдельный read-only deploy key и перейти на `git pull`.

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
