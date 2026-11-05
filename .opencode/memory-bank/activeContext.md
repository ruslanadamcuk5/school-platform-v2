# Active Context

## Текущий этап
**2.18 safety — завершён; 2.19 OpenCode — завершён; стабилизация 0.9.0.**
Дата: 2026-11-05. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `database=ok`, `jwt_ready=true`; head `0010_safety`.
- Safety UI: `dist` с `index-BkTs77yj.js`, `index-CrDWvJ6z.css`, `favicon.svg`;
  прежний — `dist.pre-router7-20261105T124346Z`; UI под school_admin: 6 вкладок,
  геолокация off, консоль/сеть чисто.
- `safety` включён: school-активация `pilot-school`; `/me/services` —
  `enabled=true`, `source=activation`; 365/1095 дней, порог 16, анонимность on,
  `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Backup активации: `20261105T103431Z-safety-activation` (дамп, dist, настройки).
- Restore-drill: временный PG 17.11, `RESTORE_EXIT=0` за 6,1 с; 78 таблиц /
  14 схем; `alembic=0010_safety`; users=217, audit=99; без `pgvector`.
- Frontend: React Router `7.18.5`; Playwright E2E 4 passed; Vitest 4; typecheck и
  build ok; `npm audit --omit=dev` — 0; dev Vitest/Vite — отдельным циклом.
- Backend: 184 passed; Ruff чистый; OpenAPI 172 пути / 232 операции.
- Документы: ШК-03-06 1.7, ШК-06-01 0.2, ШК-07-01 1.2, журнал 2.0,
  ШК-10-19 1.4; DOCX пересобран.
- OpenCode: build steps 200; `browser*`/`opencode*` выключены; `@browser`;
  секреты read-deny; `AGENTS.md` 6,4 КБ.

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
1. Redis-кеш прав/активаций и RLS/изоляция по `school_id`.
2. i18n, UI уведомлений и заявок документов.
3. Мобильный consent-flow и отдельное юридическое решение по геолокации.
4. Мажорные `vitest` 5 / `vite` 8 — отдельным регрессионным циклом.
5. При необходимости согласовать OpenCode CLI с V2.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
