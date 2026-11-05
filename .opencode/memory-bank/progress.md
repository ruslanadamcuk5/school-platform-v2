# Progress

> Только последние этапы. Полная история: `archive/progress-2026.md`.

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
- [x] Документы: ШК-07-01 — 1.0, журнал — 1.8, ШК-10-19 — 1.2;
  ШК-03-06 — 1.6.

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
