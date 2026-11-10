# Active Context

## Текущий этап
MFA для `superadmin` развёрнута на пилоте 10.11.2026; enrollment ожидает. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `version=0.9.0`, `database=ok`, `jwt_ready=true`;
  head `0011_mfa`; OpenAPI — 179 путей / 240 операций.
- Деплой MFA: backup `20261110T071428Z-mfa` (дамп 523 КБ, архивы backend и
  dist, `MANIFEST.txt`, 665 записей TOC); `MFA_ENCRYPTION_KEY` добавлен в
  `backend/.env` с правами `600`; прежний dist —
  `frontend/dist.pre-mfa-20261110T060017Z`.
- Frontend live: `index-B0rJqfB4.js`, `index-Bl5SyjTG.css`; SHA-256 совпадают
  с локальной сборкой; Vitest 11, Playwright E2E 4 passed; `npm audit` — 0.
- `safety` включён: school-активация `pilot-school`; 365/1095 дней, порог 16,
  анонимность on, `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Restore-drill safety: 78 таблиц / 14 схем, `alembic=0010_safety`.
- Backend: 216 passed; Ruff чистый. MFA: TOTP RFC 6238, Fernet, 10 резервных
  кодов, блокировка 5 попыток/15 минут, challenge-токены, аудит `mfa_*`;
  `refresh_tokens.mfa_verified` закрывает обход MFA через refresh.
- На пилоте вход `superadmin` возвращает `mfa_enrollment_required` без
  access/refresh; `enroll/start` — `200`. Enrollment и сохранение резервных
  кодов ещё не выполнены.
- Redis: managed Upstash TLS; `REDIS_URL` в `.env` (600); `cache_ping=true`;
  админ-консоль — `mode=managed-redis-tls`, `status=connected`; секрет в
  ответах отсутствует.
- Документы: ШК-00-01 0.9.6, ШК-03-01 0.4, ШК-03-03 0.18, ШК-03-06 1.9,
  ШК-04-01 0.8, ШК-05-01 0.5, ШК-06-01 0.3, ШК-07-01 1.11, ШК-08-01 1.0,
  ШК-08-02 0.8, журнал 2.9, ШК-10-19 1.5.

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
1. Выполнить enrollment `superadmin` в TOTP-приложении и сохранить 10
   резервных кодов вне сервера; проверить вход по TOTP и резервному коду.
2. Добавить безопасный reset/regeneration MFA или CLI-процедуру с аудитом
   (риск R-11).
3. Write-only endpoint/секрет и остальные параметры плана 11.3.1.
4. Production Redis: отдельный ACL, приватная сеть, резервирование и алерты.
5. RLS по `school_id`: контекст транзакции и политики для 78 таблиц; только
   с тестовой PostgreSQL.
6. i18n, UI уведомлений и заявок документов; mobile consent-flow и геолокация.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`.
