# Progress

> Только последние этапы. Полная история: `archive/progress-2026.md`.

## MFA deploy на пилот (10.11.2026)
- [x] Backup `20261110T071428Z-mfa`: дамп БД 523 КБ, архивы backend и dist,
  `MANIFEST.txt`, 665 записей TOC; head до обновления — `0010_safety`.
- [x] В `backend/.env` добавлен `MFA_ENCRYPTION_KEY` (права `600`); применена
  миграция `0011_mfa`; backend и `frontend/dist` доставлены, прежний dist —
  `frontend/dist.pre-mfa-20261110T060017Z`.
- [x] Smoke: `/health` 200/0.9.0, OpenAPI 179/240, JS/CSS-хеши совпадают с
  локальной сборкой, `/`, `/docs`, `/admin/settings`, `/robots.txt` — 200,
  старый сайт — 200; вход `superadmin` — `mfa_enrollment_required` без
  токенов, `enroll/start` — 200.
- [x] Документы: ШК-07-01 1.11, журнал 2.9, реестр 0.9.6.
- [ ] Enrollment `superadmin` в TOTP-приложении и сохранение 10 резервных
  кодов; reset/regeneration MFA остаётся (R-11).

## MFA для superadmin (10.11.2026)
- [x] TOTP RFC 6238: 30 секунд, окно ±1; секрет Fernet, ключ
  `MFA_ENCRYPTION_KEY` (fallback от `SECRET_KEY` только для разработки).
- [x] Обязательная настройка при первом входе `superadmin`; access/refresh
  выдаются только после подтверждения кода. Добавлены challenge-токены
  `mfa_token` с purpose `enroll`/`verify`.
- [x] 10 одноразовых резервных кодов (SHA-256), блокировка 5 попыток/15 минут,
  аудит `mfa_enrollment_started`, `mfa_enabled`, `mfa_verified`, `mfa_failed`.
- [x] `refresh_tokens.mfa_verified` закрывает обход MFA через refresh-сессию;
  старые токены `superadmin` без MFA отклоняются.
- [x] Миграция `0011_mfa`: поля `iam.users`, `iam.mfa_recovery_codes`,
  `iam.refresh_tokens.mfa_verified`; offline SQL проверен.
- [x] API: `/auth/mfa/enroll/start`, `/enroll/verify`, `/verify`, `/status`;
  экран входа с TOTP/резервным кодом и показом резервных кодов; бейдж MFA в
  профиле.
- [x] Тесты: backend 216 passed, frontend 11 passed; `scripts/check.ps1` —
  `OK (155s)`, Ruff/typecheck чистые; `npm run build` — ok.
- [x] Документы: ШК-03-03 0.18, ШК-03-06 1.9, ШК-04-01 0.8, ШК-05-01 0.5, ШК-07-01 1.10,
  ШК-08-01 1.0, ШК-08-02 0.8, журнал 2.8, реестр 0.9.4.
- [x] На пилот развёрнуто 10.11.2026 (см. раздел выше); enrollment
  `superadmin` и reset/regeneration остаются.

## Админ-консоль кеша — подтверждение и история (09.11.2026)
- [x] PATCH требует `confirm=true` и непустую `reason` для отключения кеша и
  смены `key_prefix`; без подтверждения — `428`, без причины — `400`.
- [x] В `audit.events` пишутся `before`, `after`, `reason` и
  `confirmed_dangerous`; секреты не попадают.
- [x] Добавлен `GET /api/v1/admin/settings/cache/history` только для
  `superadmin` + `system.settings.read`; история читается из неизменяемого
  аудита, миграция не требуется.
- [x] На `/admin/settings` добавлены блок подтверждения с причиной и история
  изменений; read-only режим сохраняется.
- [x] Тесты: backend 204 passed, frontend 9 passed; `scripts/check.ps1` —
  `OK (67,2s)`, Ruff и typecheck чистые.
- [x] Документы: ШК-03-03 0.17, ШК-07-01 1.9, ШК-08-01 0.9, ШК-08-02 0.7,
  журнал 2.7, реестр 0.9.3; на пилот не развёрнуто.
- [x] Пароль Upstash не менялся по решению пользователя от 09.11.2026.

## Админ-консоль кеша — MVP (06.11.2026)
- [x] `app/services/platform_settings.py`: типизированный snapshot
  `cache.runtime`, TTL 15 с, fallback на env, валидация TTL/префикса/таймаутов.
- [x] `app/core/cache.py`: runtime TTL, prefix, timeout и cooldown; hot-reload
  безопасных параметров; закрытие/пересоздание клиента при изменении.
- [x] API `/api/v1/admin/settings/cache` (GET/PATCH) и `/cache/test`; только
  `superadmin` + `system.settings.read/write`; аудит
  `platform.cache.settings.update`; `REDIS_URL` маскируется.
- [x] Экран `/admin/settings` и пункт меню «Эксплуатационные настройки»;
  read-only без `system.settings.write`.
- [x] Тесты: `tests/test_platform_settings.py`, `test_cache.py`;
  `PlatformSettingsPage.test.tsx`; backend 199 passed, Ruff чистый;
  frontend typecheck, build и 7 тестов.
- [x] Документы: ШК-03-03 0.16, ШК-07-01 1.8, ШК-08-01 0.8, ШК-08-02 0.6,
  журнал 2.6; индексы пересобраны.
- [x] Доставлено на пилот: backup `20261106T124815Z-admin-cache-console`
  (дамп 583 КБ, архивы backend/dist, `pg_restore -l` — 912 записей), новый
  dist `index-CHCHwh94.js` / `index-BQb1wEQh.css`; прежний —
  `dist.pre-admin-cache-console-20261106T124815Z`.
- [x] uWSGI перезапущен (master 3943074, worker 3970310); `/health` 200/0.9.0,
  `/openapi.json` 174 пути/235 операций, `/admin/settings` 200, старый сайт 200.
- [x] Под `superadmin`: GET настроек кеша — `managed-redis-tls` / `connected`,
  POST test — `ok=true` (19,6 мс), секрет в ответах отсутствует, без токена 401.
- [ ] Далее: MFA, write-only endpoint/секрет и остальные параметры плана
  11.3.1.

## Пилот 0.9.0 — развёртывание
- [x] Backup `backups/school-platform-v2/20261105T080100Z/` (БД и приложение).
- [x] Миграция `0009_document_requests` → `0010_safety`; `alembic current` = `0010_safety`.
- [x] Backend и `frontend/dist` `0.9.0` загружены; старый dist сохранён как
  `dist.pre-0.9.0-20261105T080100Z`.
- [x] `seed` выполнен; `safety` — `default_enabled=false`; выяснено, что
  country-активация уже была `enabled=true` (уточнение к записи №64);
  `.env` и `secrets` не перезаписаны.
- [x] `/health` — `0.9.0`, `status=ok`.
- [x] Деплой записан в `docs/07-operations/01-razvertyvanie-i-ekspluataciya.md`;
  журнал изменений 1.6 (записи 64–65); подготовлен отчёт ШК-10-20.
- [x] DOCX `v0.9.0` пересобран: 47 отдельных файлов и объединённый
  `docs/word/ЕОРП_ВЕКТОР_Полный_пакет_документации_v0.9.0.docx`.

## Safety UI и активация на пилоте (05.11.2026)
- [x] Экран `/safety`: обращения, инциденты, согласия, геолокация,
  настройки; role-gating, состояния сервиса и выбора школы.
- [x] Клиент `fetchSafetySettings`/`updateSafetySettings`/`purgeSafetyData`;
  типы настроек и результата очистки.
- [x] Vitest + React Testing Library: 4 теста; `npm test` зелёный.
- [x] Backup `backups/school-platform-v2/20261105T103431Z-safety-activation/`
  (дамп БД, архив прежнего dist, снимок активаций и настроек).
- [x] Новый `frontend/dist` доставлен; прежний —
  `dist.pre-safety-ui-20261105T103431Z`; SHA-256 совпадают с локальной сборкой.
- [x] Создана school-активация `safety` для `pilot-school`; `/me/services` —
  `enabled=true`, `source=activation`.
- [x] Глобальная геолокация выключена; остальные настройки — 365/1095 дней,
  порог 16 лет, анонимные обращения разрешены.
- [x] Smoke: `/health`, `/safety`, JS/CSS и read-only маршруты `safety` — `200`.
- [x] Favicon `frontend/public/favicon.svg` и ссылка в `index.html`; dist
  пересобран, прежний — `dist.pre-favicon-20261105T113013Z`.
- [x] UI `/safety` проверен headless Edge под school_admin: вход, 6 вкладок,
  геолокация off, анонимность on, консоль/сеть без ошибок; `404 favicon.ico`
  устранён.
- [x] Документы: ШК-07-01 — 1.2, журнал — 2.0, ШК-10-19 — 1.4;
  ШК-03-06 — 1.7; DOCX `v0.9.0` пересобран (47 + combined).
- [x] Коммиты `b288138`, `0dfc629`, `165cf70`, `385045f`, `c46bed1`,
  `3478d3a`, `95c6bca`; push в `origin/main`.

## Стабилизация 0.9.0 (05.11.2026)
- [x] Playwright E2E: `frontend/e2e`, env-логин, storage state gitignored;
  4 read-only сценария на пилоте — passed.
- [x] React Router `7.18.5`; удалены `future`-флаги; typecheck, Vitest, build
  и E2E зелёные; production-аудит — 0.
- [x] Деплой router-сборки: `index-BkTs77yj.js`, backup
  `dist.pre-router7-20261105T124346Z`.
- [x] Restore-drill: временный PostgreSQL 17.11, `RESTORE_EXIT=0` за 6,1 с;
  78 таблиц / 14 схем; `alembic=0010_safety`; users=217, audit=99.
- [x] Vite `8.3.6`, Vitest `5.1.0`, plugin-react `6.2.1`, jsdom `28.1.0`;
  build `index-BaAbEN3E.js`, backup `dist.pre-vite8-20261105T133933Z`;
  E2E 4 passed, `npm audit` — 0.
- [x] `opencode.json`: build steps увеличены с 50 до 200.
- [x] Redis-кеш прав/активаций: `REDIS_URL`, TTL 60 с, версионная
  инвалидация, fail-open, circuit breaker; локальный Redis 8.10.3,
  `scripts/redis-local.ps1`, 9 тестов кеша, реальный smoke.
- [x] В pilot/production удалённый Redis обязан быть `rediss://`; plaintext
  loopback разрешён только для локальной разработки.
- [x] Backend `193 passed`, Ruff чистый; OpenAPI без изменений.
- [x] План: обязательное администрирование кеша и эксплуатационных настроек
  республиканским администратором (ШК-08-01 0.7, ШК-08-02 0.5).
- [x] Managed Upstash Redis по TLS подключён на пилоте; `REDIS_URL` в
  `backend/.env` (600), backup `20261106T062733Z-upstash-redis`.
- [x] Restart пилота выполнен: master 2931184; `cache_ping=true`,
  `connected_clients=2`, версия ключа создана; `/health`, `/docs` и старый
  сайт — 200.
- [ ] Сменить пароль Upstash, так как он был передан в чате.
- [ ] Production Redis: отдельный ACL, приватная сеть, резервирование, алерты.
- [ ] RLS по `school_id`: отдельный цикл, контекст транзакций и 78 таблиц.
- [ ] Мобильный consent-flow и геолокация: ждут юридического решения.

## Этап 2.18 — безопасность и психологическая поддержка
- [x] Миграция `0010_safety`: обращения, инциденты, геолокация, согласия,
  `iam.users.date_of_birth`.
- [x] API обращений (включая анонимные), инцидентов, согласий, геолокации,
  настроек и очистки по срокам.
- [x] Права `safety.*` и `safety.settings.manage`; проверка активации.
- [x] Правила Закона № 99-З: порог 16 лет, согласие представителя, сроки хранения.
- [x] Backend `184 passed`, Ruff чистый; frontend typecheck и production build.
- [x] Экран `/safety` и клиентские методы настроек/очистки; Vitest — 4 теста.
- [x] OpenAPI `0.9.0`: 172 пути / 232 операции.
- [x] `npm audit`: 8 предупреждений, 2 critical в dev Vitest/Vite; production —
  2 moderate `react-router` 6.x; мажорные обновления отложены.
- [x] Отчёт ШК-10-19 (1.2); журнал изменений 1.8.

## Этап 2.19 — экономия токенов и OpenCode
- [x] `AGENTS.md` сокращён с 8,3 КБ до 6,4 КБ; `progress.md` сжат, история
  перенесена в `archive/progress-2026.md`.
- [x] Индексы: `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/api/ENDPOINTS.md`.
- [x] Skills, команды, подагенты и `scripts/check.ps1`; проверка запускает
  frontend-тесты.
- [x] Агрессивный пакет OpenCode: `model=opencode/deepseek-v4.1-flash-free`;
  `browser*`/`opencode*` выключены, добавлен `@browser`;
  подагенты `explorer`/`test-runner`/`docs-writer` — на бесплатной модели;
  команды `/check`, `/test`, `/docs`, `/api`, `/release`, `/db-schema`,
  `/pilot-status` — `subtask`;
  безопасный bash-allowlist; `task`-ограничения; лимиты `steps`;
  read-deny для секретов; расширенный watcher.
- [x] Глобальный `opencode.json` исправлен; зависавший plugin `opencode-puter-auth`
  убран из автозагрузки.
- [x] Диагностика БД: локальная `opencode.db` — V2 (`session_v2`, 50 миграций,
  9 сессий), CLI `1.19.4` — V1, поэтому `opencode db/models` падают.
  Backup БД сделан; destructive-действия не выполнялись.
- [ ] Согласовать CLI с V2 (`opencode upgrade --major`) — отдельное решение.
- [x] API не изменялся; версия остаётся `0.9.0`.

## Этап 3 — расширение
- [~] Электронный журнал: API расписания, оценок и посещаемости; UI — далее.
- [ ] Ограничить сводку ступени своим классом/ребёнком.
- [ ] Родительский кабинет и GPS.
- [ ] Мессенджер и видео.
- [~] Документы: API заявок и клиент готовы; UI и подпись — далее.
- [ ] Методист и AI-валидация.
- [~] Психолог и безопасность: API и UI готовы, сервис включён на пилоте;
  геолокация выключена, чат и мобильный consent-flow — далее.
- [ ] Иерархия администраторов.

## Этап 4 — мобильные клиенты
- [ ] Flutter Android/iOS.
- [ ] Offline sync.
- [ ] Push, Force Update.
- [ ] Публикация в сторах.

## Этап 5 — зрелость
- [ ] Интеграции с государственными системами.
- [ ] Отчётность и BI.
- [ ] Нагрузочное тестирование.
- [ ] Аттестация СЗИ.
- [ ] Пилот и ввод в эксплуатацию.
