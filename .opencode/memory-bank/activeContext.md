# Active Context

## Текущий этап
**2.18 safety — завершён; 2.19 OpenCode — завершён; админ-консоль кеша — развёрнута на пилоте; подтверждение и история изменений — готовы.**
Дата: 2026-11-09. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `version=0.9.0`, `database=ok`, `jwt_ready=true`;
  head `0010_safety`. Админ-консоль кеша развёрнута 06.11.2026.
- Frontend: React Router `7.18.5`, Vite `8.3.6`, Vitest `5.1.0`; Playwright E2E
  4 passed; Vitest 9 (5 для `/admin/settings`); typecheck и build ok;
  `npm audit` — 0 (prod + dev). Живой dist: `index-CHCHwh94.js`,
  `index-BQb1wEQh.css`; прежний — `dist.pre-admin-cache-console-20261106T124815Z`.
- `safety` включён: school-активация `pilot-school`; 365/1095 дней, порог 16,
  анонимность on, `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Backup деплоя: `20261106T124815Z-admin-cache-console` (дамп БД 583 КБ,
  архивы backend и dist, `MANIFEST.txt`, `pg_restore -l` — 912 записей).
- Restore-drill safety: временный PG 17.11, `RESTORE_EXIT=0` за 6,1 с; 78 таблиц /
  14 схем; `alembic=0010_safety`; users=217, audit=99; без `pgvector`.
- Backend: 204 passed; Ruff чистый. OpenAPI локально — 175 путей / 236 операций
  (на пилоте 174/235 до деплоя); добавлены
  `GET /api/v1/admin/settings/cache/history`, подтверждение опасных изменений
  (`confirm` + `reason`) и снимки `before`/`after` в аудите.
- `scripts/check.ps1` 09.11.2026 — `OK (67,2s)`: Ruff, 204 backend-теста,
  typecheck, 9 frontend-тестов.
- Redis: managed Upstash TLS подключён на пилоте; `REDIS_URL` в `.env` (600),
  backup `20261106T062733Z-upstash-redis`; uWSGI graceful respawn — master
  `3943074`, worker `3970310`; `cache_ping=true`, `connected_clients=2`.
  Локально 8.10.3, 9 тестов кеша. `GET /api/v1/admin/settings/cache` под
  `superadmin` — `mode=managed-redis-tls`, `status=connected`; `POST /cache/test`
  — `ok=true`; секрет в ответах отсутствует.
- Документы: ШК-00-01 0.9.3, ШК-03-01 0.4, ШК-03-03 0.17, ШК-03-06 1.8,
  ШК-05-01 0.4, ШК-06-01 0.3, ШК-07-01 1.9, ШК-08-01 0.9, ШК-08-02 0.7,
  журнал 2.7, ШК-10-19 1.5.
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
1. MFA для `superadmin`, write-only endpoint/секрет и остальные параметры
   плана 11.3.1.
2. Production Redis: отдельный ACL, приватная сеть, резервирование и алерты.
3. RLS по `school_id`: контекст транзакции и политики для 78 таблиц; только
   с тестовой PostgreSQL.
4. i18n, UI уведомлений и заявок документов; mobile consent-flow и геолокация.

Смена пароля Upstash отложена по решению пользователя от 09.11.2026
(«не менять пока необязательно»).

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
