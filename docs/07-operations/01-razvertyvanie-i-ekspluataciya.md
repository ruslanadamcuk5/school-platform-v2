# Развёртывание и эксплуатация

| Параметр | Значение |
|---|---|
| Код документа | ШК-07-01 |
| Версия | 1.3 |
| Статус | Рабочий |
| Дата | 05.11.2026 |

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
- Миграция: `0005_curricula (head)`.
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
9. Перезапустить сайт: **Web → Sites → school-platform-v2 → Restart**
   (круглая стрелка). Если кнопка не отображается, изменить любую переменную
   в **Environment** и сохранить форму — сохранение настроек сайта перезапускает
   uWSGI. Горячая перезагрузка Python-кода не включена (`py-autoreload`),
   поэтому после замены файлов backend перезапуск обязателен.
10. Проверить `/health`, `/`, `/groups`, `/docs`, `/robots.txt`, старый сайт.

При обновлении backend без пересоздания сайта:
1. Доставить каталог `backend/` через `scp` или `git pull`.
2. При изменении каталога прав или групп выполнить `python -m app.db.seed`.
3. Перезапустить сайт кнопкой **Restart** или сохранением **Environment**.
4. Проверить `/health` и один защищённый маршрут; отключение сервиса должно
   возвращать `403` с текстом `Service '<code>' is disabled for this scope`.

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

### 3.4.2. Состояние пилота на 03.11.2026
- Перед обновлением создан архив:
  `/home/school-platform-v2/backups/school-platform-v2/2026-11-03/`;
  отдельно сохранён `backend-app-pre-pilot-data-2026-11-03.tgz`.
- Доставлены `backend/app`, `backend/alembic`, `backend/alembic.ini` и
  `frontend/dist`; `.env`, `secrets/` и содержимое WSGI-адаптера не изменялись.
- Миграция `0005_curricula` применена, `alembic current` показывает head.
- Живой OpenAPI: версия `0.8.0`, 113 путей, 38 маршрутов ступеней
  образования, включая `curricula` и `components`.
- `/health` — `200`, БД `ok`; `/` — `200`; JS/CSS-хеши совпадают с локальной
  production-сборкой.
- В пилотную PostgreSQL загружены синтетические данные всех четырёх ступеней:
  3 учреждения, 19 классов/групп, 217 пользователей, 4 программы, 4 учебных
  плана, 59 компонентов, 72 профиля обучающихся, 16 профилей преподавателей,
  30 предметов, 232 темы, 136 слотов расписания, 1840 записей журнала,
  68 учебников и 68 библиотечных карточек.
- Данные помечены `synthetic_pilot_2026`; реальные персональные данные не
  используются. Демо-логины и пароли находятся только в игнорируемом
  `backend/secrets/pilot_demo_credentials.csv`.
- Повторный запуск `python -m app.db.pilot_data` идемпотентен и не создаёт
  дубликатов.
- Живые проверки: `primary` — 32 ученика и 4 группы; `secondary` — 56 учеников
  и 7 групп; `vocational` — 40 учеников, 4 группы, 2 программы; `higher` —
  32 ученика, 4 группы, 2 программы. Учебные планы: 2 + 2, компоненты:
  27 + 32. `/analytics/overview` — 88 учеников и 11 классов;
  `/journal/schedule` — 88 слотов; `/library` — `200`.
- После доставки исправления наследования прав WSGI-процесс перезагружен
  через `touch backend/__init__.py`; администратор школы получает 75 прав,
  ученик — 13. Если изменения не применяются, использовать
  **Web → Sites → school-platform-v2 → Restart**.
- Визуальная проверка экранов `/education/primary`, `/education/secondary`,
  `/education/vocational` и `/education/higher` подтвердила отображение
  учеников, групп, программ, академических профилей и учебных планов.
  Планы раскрываются до компонентов; профили преподавателей видны.

### 3.4.3. Развёрнуто 04.11.2026 (версия 0.8.3)
- На пилот доставлены backend и `frontend/dist` версии `0.8.3`, применены
  миграции `0006_sessions_credits`, `0007_competencies`,
  `0008_practice_contracts`, `0009_document_requests`; head — `0009`.
- Выполнены `python -m app.db.seed` (добавлены 2 права) и
  `python -m app.db.pilot_data` (синтетические сессии, ведомости, перезачёты,
  компетенции, предприятия, договоры, практиканты и дневники).
- Предыдущий `dist` сохранён как
  `frontend/dist.pre-0.8.3-20261104T115718Z`.
- Backup: `/home/school-platform-v2/school-platform-v2/backups/
  school-platform-v2/20261104T115542Z/` (архив приложения и дамп БД).
- `/health` — `200` и `0.8.3`; старая площадка
  `https://virusadk.alwaysdata.net/healthz` — `200`.
- `documents` остаётся отключённым для школы пилота и отдаёт `403` до
  активации республиканским администратором.

### 3.4.4. Развёрнуто 05.11.2026 (версия 0.9.0)
- Создан backup
  `/home/school-platform-v2/school-platform-v2/backups/school-platform-v2/20261105T080100Z/`
  с архивом приложения и дампом БД.
- Применена миграция `0010_safety` после `0009_document_requests`;
  `alembic current` — `0010_safety`. Созданы таблицы
  `safety.support_appeals`, `safety.incidents`, `safety.geolocation_points`,
  `safety.consents` и колонка `iam.users.date_of_birth`.
- На пилот доставлены backend и `frontend/dist` версии `0.9.0`; предыдущий
  `dist` сохранён как `frontend/dist.pre-0.9.0-20261105T080100Z`.
- Выполнен `python -m app.db.seed`; сервис `safety` остаётся выключенным:
  `default_enabled=false`, активаций для школ нет. `.env` и `secrets` не
  перезаписывались.
- `/health` — `200`, `version=0.9.0`, `database=ok`, `jwt_ready=true`;
  `/openapi.json` — `0.9.0`, 172 пути и 232 операции, 11 путей (16 операций)
  безопасности; `/`, `/docs` и `/robots.txt` — `200`.
- `safety` не активирован; включение выполняется только отдельным
  распоряжением республиканского администратора для конкретной школы.
- Откат: восстановить backup, вернуть
  `frontend/dist.pre-0.9.0-20261105T080100Z` и при необходимости выполнить
  `alembic downgrade 0009_document_requests`.

### 3.4.5. Развёрнуто 05.11.2026 (safety UI и активация)
- Создан backup
  `/home/school-platform-v2/school-platform-v2/backups/school-platform-v2/20261105T103431Z-safety-activation/`:
  дамп БД `db-pre-safety-activation-20261105T103431Z.dump` — 581 КБ,
  архив прежнего frontend
  `frontend-dist-pre-safety-ui-20261105T103431Z.tgz` — 161 КБ,
  снимок активаций и настроек `safety-state-before.json`.
- Собран и доставлен новый `frontend/dist` с экраном `/safety`:
  `index-CAJYbBBE.js` — 662 734 байта, `index-CrDWvJ6z.css` — 45 588 байт;
  SHA-256 совпадают с локальной production-сборкой. Предыдущий каталог
  сохранён как `frontend/dist.pre-safety-ui-20261105T103431Z`.
- Сервис `safety` уже имел country-активацию `enabled=true`; дополнительно
  создана явная school-активация для `pilot-school`
  (`0064759a-d6ea-4e5b-b4a3-0033e91f5efe`): `enabled=true`, `config={}`.
  `/api/v1/me/services` возвращает `safety: enabled=true, source=activation`.
- Глобальные настройки: хранение обращений 365 дней, инцидентов 1095 дней,
  порог согласия 16 лет, анонимные обращения разрешены,
  `geolocation_enabled=false` до отдельного юридического решения и готовности
  мобильного consent-flow.
- Smoke-проверки: `/health` — `200`, `version=0.9.0`, `database=ok`,
  `jwt_ready=true`; `/safety` и новые JS/CSS — `200`; `/openapi.json` —
  `0.9.0`, 172 пути и 232 операции; read-only маршруты `safety` для
  `pilot-school` (свои обращения, обращения школы, инциденты, согласия,
  геолокация) — `200`, списки пусты.
- Уточнение к записи №64: утверждение «активаций нет» было ошибочным —
  country-активация `safety` уже существовала и была включена.
- Откат: восстановить дамп БД из backup (возвращает отсутствие school-строки
  и `geolocation_enabled=true`) либо удалить school-активацию и вернуть
  настройку; вернуть `frontend/dist.pre-safety-ui-20261105T103431Z`.
  Миграции и backend в этом изменении не затрагивались, перезапуск не нужен.

### 3.4.6. Проверка UI и favicon (05.11.2026)
- В `frontend/index.html` добавлена ссылка на `/favicon.svg`, создан
  `frontend/public/favicon.svg`; production-сборка содержит `favicon.svg`
  (232 байта) и `index.html` (755 байт), JS/CSS-хеши не изменились.
- Прежний `dist` сохранён как `dist.pre-favicon-20261105T113013Z`,
  дополнительный архив —
  `backups/school-platform-v2/dist-pre-favicon-20261105T113013Z.tgz`.
- Выполнена реальная UI-проверка headless Edge под синтетическим
  school_admin: вход успешен, `/safety` показывает «сервис включён»,
  доступны все шесть вкладок, геолокация выключена, анонимные обращения
  включены; ошибок консоли, page errors и неуспешных ответов нет.
- `/favicon.svg` — `200`, `image/svg+xml`; прежняя ошибка `404 favicon.ico`
  устранена.
- Проверки frontend: `npm test` — 4 passed, `npm run build` — успешно.
- Откат: вернуть `dist.pre-favicon-20261105T113013Z` или распаковать архив;
  backend и миграции не затрагивались.

### 3.4.7. React Router 7.18.5 и E2E (05.11.2026)
- `react-router-dom` обновлён с 6.x до `7.18.5`; удалены устаревшие
  `future`-флаги `BrowserRouter`/`MemoryRouter`.
- Проверки: `tsc --noEmit`, Vitest — 4 passed, production build; новый JS —
  `index-BkTs77yj.js`.
- `npm audit --omit=dev` — 0 уязвимостей; dev-предупреждения Vitest/Vite
  остаются и требуют отдельного мажорного цикла.
- Добавлен Playwright-smoke: `frontend/e2e`, `npm run test:e2e`; вход через
  `PILOT_LOGIN`/`PILOT_PASSWORD`, storage state в gitignored
  `frontend/e2e/.auth/user.json`.
- E2E на пилоте: 4 passed — вход, `/safety`, 6 вкладок, настройки
  (геолокация off, анонимность on), клиентская навигация.
- Прежний dist: `dist.pre-router7-20261105T124346Z`; архив —
  `backups/school-platform-v2/dist-pre-router7-20261105T124346Z.tgz`.
- Откат: вернуть прежний dist или распаковать архив; backend и миграции
  не затрагивались.

### 3.4.8. Проверка восстановления backup (05.11.2026)
- Использован дамп
  `backups/school-platform-v2/20261105T103431Z-safety-activation/db-pre-safety-activation-20261105T103431Z.dump`.
- Локально развёрнут временный PostgreSQL 17.11 (переносимые бинарники,
  без службы и без production), восстановление — `pg_restore --no-owner
  --no-privileges --exit-on-error`.
- Результат: `RESTORE_EXIT=0`, время — 6,1 с; 78 таблиц в 14 схемах;
  `alembic_version` — `0010_safety`; `iam.users` — 217, `audit.events` — 99,
  `org.schools` — 3, `system.services` — 19; размер БД — 17 МБ.
- Ограничение: локальный PostgreSQL не содержит расширение `pgvector`,
  поэтому `CREATE EXTENSION vector` исключён из тестового TOC; таблицы и
  данные restored без ошибок. Полная проверка с `pgvector` — в контуре,
  где расширение установлено.
- Временный кластер остановлен и удалён; production не затрагивался.

### 3.4.9. Vite 8 и Vitest 5 (05.11.2026)
- Обновлены `vite` 8.3.6, `vitest` 5.1.0, `@vitejs/plugin-react` 6.2.1,
  `jsdom` 28.1.0; Node 22.14 совместим с выбранными версиями.
- Проверки: typecheck, Vitest — 4 passed, production build; новый JS —
  `index-BaAbEN3E.js`, CSS — `index-BNJdgJYo.css`.
- `npm audit` — 0 уязвимостей, включая dev-зависимости.
- E2E на пилоте после деплоя — 4 passed.
- Прежний dist: `dist.pre-vite8-20261105T133933Z`; архив —
  `backups/school-platform-v2/dist-pre-vite8-20261105T133933Z.tgz`.
- Откат: вернуть прежний dist или распаковать архив; backend и миграции
  не затрагивались.

### 3.5. Ограничения пилота
Alwaysdata подходит для пилота и демонстрации, но не заменяет
аттестованный ЦОД для промышленной эксплуатации. Для промышленного контура
требуется отдельная инфраструктура на территории Республики Беларусь.
В пилоте нет Redis, фоновых задач, rate limiting и WAF уровня приложения;
внешние AI-сервисы выключены. Пароль супер-администратора хранится в
`backend/.env` и должен быть сменён после передачи заказчику.
- `npm audit` на 05.11.2026 после React Router 7.18.5, Vite 8 и Vitest 5 —
  0 уязвимостей, включая dev-зависимости.

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
