# Active Context

## Текущий этап
**2.18. Безопасность и психологическая поддержка — завершён.
2.19. Экономия токенов и OpenCode — завершён.**
Дата: 2026-11-05. Версия API/frontend: `0.9.0`.

## Состояние
- Пилот: `0.9.0`; `/health` — `ok`, `database=ok`, `jwt_ready=true`;
  head `0010_safety`; backup `20261105T080100Z`.
- Safety UI развёрнут: `frontend/dist` с `index-CAJYbBBE.js`,
  `index-CrDWvJ6z.css` и `favicon.svg`; прежний dist —
  `dist.pre-favicon-20261105T113013Z` (ранее
  `dist.pre-safety-ui-20261105T103431Z`).
- UI `/safety` проверен headless Edge под school_admin: сервис включён,
  6 вкладок, геолокация off, анонимность on, консоль/сеть без ошибок;
  `404 favicon.ico` устранён.
- `safety` включён: country-активация уже была `enabled=true`; добавлена
  явная school-активация для `pilot-school` (`enabled=true`).
  `/me/services` — `enabled=true`, `source=activation`.
- Глобальные настройки safety: 365/1095 дней, порог 16 лет, анонимные
  обращения разрешены, `geolocation_enabled=false` до отдельного
  юридического решения и мобильного consent-flow.
- Backup активации:
  `backups/school-platform-v2/20261105T103431Z-safety-activation/` — дамп БД,
  архив прежнего dist, снимок активаций и настроек.
- Локально: backend `184 passed`; Ruff чистый; frontend typecheck/build
  успешны; Vitest — 4 теста `/safety`; OpenAPI `172` пути / `232` операции.
- Документы: v0.9.0; ШК-07-01 — 1.1; журнал — 1.9; ШК-10-19 — 1.3;
  ШК-03-06 — 1.6; DOCX пересобран.
- Аудит: 8 предупреждений (2 critical — dev Vitest/Vite); production —
  2 moderate в `react-router` 6.x. Мажорные обновления — отдельным циклом.
- OpenCode: профиль `deepseek-v4.1-flash-free`; `browser*`/`opencode*`
  выключены, для UI есть `@browser`; подагенты на бесплатной модели; команды
  через `subtask`; bash-allowlist; лимиты шагов; read-deny секретов.
- `AGENTS.md` — 6,4 КБ; `progress.md` сжат, история в `archive/progress-2026.md`.
- OpenCode DB: V2 против CLI `1.19.4` (V1); backup есть, destructive не было.

## Инварианты
- Не трогать `C:\Users\adamrv\Documents\edu-math`, его БД и процессы.
- Не менять `virusadk.alwaysdata.net`.
- Не коммитить секреты, токены, пароли, реальные ПДн.
- Пилотные данные синтетические (`synthetic_pilot_2026`).
- `safety` включён на пилоте по явной команде; геолокация выключена.
  Включение геолокации и других контуров — только отдельным решением.
- API-first; `school_id`; RBAC; аудит; professional features только
  `vocational`/`higher`.
- Любое изменение API — в `docs/10-reporting/04-zhurnal-izmeneniy.md`.

## Следующие задачи
1. E2E Playwright, i18n, Redis-кеш прав, RLS; затем UI уведомлений/документов.
2. Мобильный consent-flow и отдельное юридическое решение по геолокации.
3. Регрессионный цикл для мажорных `react-router-dom` 7, `vitest` 5,
   `vite` 8; `audit fix --force` не применять.
4. При необходимости согласовать OpenCode CLI с V2 (`opencode upgrade --major`).

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
