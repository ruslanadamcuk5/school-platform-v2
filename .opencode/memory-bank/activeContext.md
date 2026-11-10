# Active Context

## Текущий этап
**2.18 safety — завершён; 2.19 OpenCode — завершён; админ-консоль кеша — развёрнута на пилоте; MFA для `superadmin` — реализована, на пилот не развёрнута.**
Дата: 2026-11-10. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `version=0.9.0`, `database=ok`, `jwt_ready=true`;
  head `0010_safety`. Админ-консоль кеша развёрнута 06.11.2026.
- Frontend: React Router `7.18.5`, Vite `8.3.6`, Vitest `5.1.0`; Playwright E2E
  4 passed; Vitest 11 (5 для `/admin/settings`, 2 для MFA-входа); typecheck и
  build ok; `npm audit` — 0 (prod + dev). Локальный dist:
  `index-B0rJqfB4.js`, `index-Bl5SyjTG.css`; на пилоте пока
  `index-CHCHwh94.js`, `index-BQb1wEQh.css`.
- `safety` включён: school-активация `pilot-school`; 365/1095 дней, порог 16,
  анонимность on, `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Backup деплоя: `20261106T124815Z-admin-cache-console` (дамп БД 583 КБ,
  архивы backend и dist, `MANIFEST.txt`, `pg_restore -l` — 912 записей).
- Restore-drill safety: временный PG 17.11, `RESTORE_EXIT=0` за 6,1 с; 78 таблиц /
  14 схем; `alembic=0010_safety`; users=217, audit=99; без `pgvector`.
- Backend: 216 passed; Ruff чистый. OpenAPI локально — 179 путей / 240 операций
  (на пилоте 174/235 до деплоя). Добавлены MFA-эндпоинты
  `/auth/mfa/enroll/start`, `/enroll/verify`, `/verify`, `/status`; миграция
  `0011_mfa` (не применена к пилоту).
- MFA: TOTP RFC 6238, Fernet-шифрование секрета, 10 резервных кодов, блокировка
  5 попыток/15 минут, challenge-токены, аудит `mfa_*`. `superadmin` без MFA
  получает `mfa_enrollment_required` и не получает access/refresh до
  подтверждения кода. `refresh_tokens.mfa_verified` закрывает обход MFA.
- `scripts/check.ps1` 10.11.2026 — `OK (155s)`: Ruff, 216 backend-тестов,
  typecheck, 11 frontend-тестов; `npm run build` — ok.
- Redis: managed Upstash TLS подключён на пилоте; `REDIS_URL` в `.env` (600),
  backup `20261106T062733Z-upstash-redis`; uWSGI graceful respawn — master
  `3943074`, worker `3970310`; `cache_ping=true`, `connected_clients=2`.
  Локально 8.10.3, 9 тестов кеша. `GET /api/v1/admin/settings/cache` под
  `superadmin` — `mode=managed-redis-tls`, `status=connected`; `POST /cache/test`
  — `ok=true`; секрет в ответах отсутствует.
- Документы: ШК-00-01 0.9.5, ШК-03-01 0.4, ШК-03-03 0.18, ШК-03-06 1.9,
  ШК-04-01 0.8, ШК-05-01 0.5, ШК-06-01 0.3, ШК-07-01 1.10, ШК-08-01 1.0,
  ШК-08-02 0.8, журнал 2.8, ШК-10-19 1.5.
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
1. Развернуть MFA на пилоте только по отдельной команде: backup, миграция
   `0011_mfa`, `MFA_ENCRYPTION_KEY`, enrollment `superadmin`, smoke.
2. Write-only endpoint/секрет и остальные параметры плана 11.3.1.
3. Production Redis: отдельный ACL, приватная сеть, резервирование и алерты.
4. RLS по `school_id`: контекст транзакции и политики для 78 таблиц; только
   с тестовой PostgreSQL.
5. i18n, UI уведомлений и заявок документов; mobile consent-flow и геолокация.

Смена пароля Upstash отложена по решению пользователя от 09.11.2026
(«не менять пока необязательно»).

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
