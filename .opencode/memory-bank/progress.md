# Progress

> Только последние этапы. Полная история: `archive/progress-2026.md`.

## Этап 2.17 — заявки документов и секретариат
- [x] Добавлена миграция `0009_document_requests` и таблица `documents.document_requests`.
- [x] API своих заявок, заявок школы, создания, обработки и отмены.
- [x] Проверки активации `documents`, прав, связи родителя с ребёнком и принадлежности школе.
- [x] Типы и функции веб-клиента для заявок документов.
- [x] Backend `159 passed`, Ruff чистый; frontend typecheck и production build успешны.
- [x] Alembic offline SQL `0009_document_requests` сгенерирован успешно.
- [x] OpenAPI `0.8.3`: 161 путь и 216 операций.
- [x] DOCX-пакет v0.8.3 пересобран; добавлен отчёт ШК-10-18.
- [x] Коммит `1fc0049` отправлен в `origin/main`.

## Пилот 0.8.3 — развёртывание
- [x] Применены миграции `0006`–`0009`; head `0009_document_requests`.
- [x] Выполнены `python -m app.db.seed` и `python -m app.db.pilot_data`.
- [x] Обновлён `frontend/dist`; старый сохранён как `dist.pre-0.8.3-20261104T115718Z`.
- [x] Backup `backups/school-platform-v2/20261104T115542Z/` (приложение и БД).
- [x] `/health` — `200` и `0.8.3`; старая площадка `virusadk.alwaysdata.net/healthz` — `200`.
- [x] `documents` остаётся отключённым и отдаёт `403` до активации.

## Этап 2.18 — безопасность и психологическая поддержка
- [x] Добавлена миграция `0010_safety`: `safety.support_appeals`, `safety.incidents`, `safety.geolocation_points`, `safety.consents`, `iam.users.date_of_birth`.
- [x] API обращений (включая анонимные), инцидентов, согласий, геолокации, настроек ограничений и очистки по срокам.
- [x] Права `safety.*` и `safety.settings.manage`; проверка активации сервиса.
- [x] Правила Закона № 99-З: порог согласия 16 лет, согласие законного представителя, запрет понижения порога, сроки хранения.
- [x] Типы и функции веб-клиента для безопасности.
- [x] Backend `184 passed`, Ruff чистый; frontend typecheck и production build успешны.
- [x] Alembic offline SQL `0010_safety` сгенерирован успешно.
- [x] OpenAPI `0.9.0`: 172 пути и 232 операции.
- [x] Отчёт ШК-10-19; журнал изменений обновлён до 1.4.
- [ ] Миграция `0010` и код `safety` на пилот не доставлялись — ждут отдельной команды.

## Этап 2.19 — экономия токенов
- [x] `AGENTS.md`: порядок чтения, запреты и бюджет контекста.
- [x] Memory bank 2.0: `activeContext.md` ≤ 4 КБ, история — в `archive/progress-2026.md`.
- [x] Индексы: `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/api/ENDPOINTS.md`.
- [x] Генераторы: `scripts/gen_docs_index.py`, `scripts/gen_codemap.py`, `scripts/gen_api_index.py`.
- [x] Skills: `add-endpoint`, `add-migration`, `add-service`, `docs-sync`, `release`, `pilot-deploy`, `test-triage`.
- [x] Commands: `/check`, `/test`, `/docs`, `/api`, `/release`, `/pilot-status`, `/db-schema`.
- [x] Subagents: `explorer`, `reviewer`, `test-runner`, `docs-writer`.
- [x] `scripts/check.ps1` — единая проверка ruff + pytest + typecheck.
- [x] `opencode.json`: `compaction.prune`, `watcher.ignore`, запрет чтения `docs/word`, `node_modules`, `.venv`, `backups`, `.env`.
- [x] MinGit 2.56 добавлен в пользовательский `PATH`.
- [x] Context7 MCP подключён; ключ сохранён в User env и проверен (API 200).
- [x] API не изменялся; версия остаётся `0.9.0`.

## Этап 3 — расширение
- [~] Электронный журнал: базовое API расписания, оценок и посещаемости готово; UI и расширения — далее.
- [ ] Ограничить сводку ступени для ученика/родителя своим классом/ребёнком (сейчас доступны агрегаты и список групп всей школы без ПДн обучающихся).
- [ ] Родительский кабинет и GPS.
- [ ] Мессенджер и видео.
- [~] Документы и секретариат: API заявок и клиент готовы; UI, шаблоны и подпись — далее.
- [ ] Методист и AI-валидация.
- [~] Психолог и безопасность: API, согласия, инциденты и геолокация готовы; UI и чат — далее.
- [ ] Иерархия администраторов.

## Этап 4 — мобильные клиенты
- [ ] Flutter Android.
- [ ] Flutter iOS.
- [ ] Offline sync.
- [ ] Push, Force Update.
- [ ] Публикация в сторах.

## Этап 5 — зрелость
- [ ] Интеграции с государственными системами.
- [ ] Отчётность и BI.
- [ ] Нагрузочное тестирование.
- [ ] Аттестация СЗИ.
- [ ] Пилот и ввод в эксплуатацию.
