# Active Context

## Текущий этап
MFA для `superadmin` развёрнута на пилоте 10.11.2026; enrollment выполнен. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `version=0.9.0`, `database=ok`, `jwt_ready=true`;
  head `0011_mfa`; OpenAPI — 179 путей / 240 операций.
- Деплой MFA: backup `20261110T071428Z-mfa`; `MFA_ENCRYPTION_KEY` в
  `backend/.env` (600); прежний dist — `frontend/dist.pre-mfa-20261110T060017Z`.
- Frontend live: `index-B0rJqfB4.js`, `index-Bl5SyjTG.css`; хеши совпадают;
  Vitest 11, E2E 4 passed; `npm audit` — 0.
- `safety` включён: school-активация `pilot-school`; 365/1095 дней, порог 16,
  анонимность on, `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Backend: 219 passed; Ruff чистый. MFA: TOTP RFC 6238, Fernet, 10 резервных
  кодов, блокировка 5 попыток/15 минут, challenge-токены, аудит `mfa_*`;
  `refresh_tokens.mfa_verified` закрывает обход MFA через refresh.
- Emergency reset CLI развёрнут: `status` и `reset --dry-run` проверены;
  reset требует `--confirm`/причину, отзывает refresh, удаляет коды, пишет
  `mfa_reset`; фактический reset не выполнялся.
- На пилоте `superadmin`: `mfa_enabled=True`, 10 резервных кодов; вход
  возвращает `mfa_required` без access/refresh.
- Redis: managed Upstash TLS; `REDIS_URL` в `.env` (600); `cache_ping=true`;
  админ-консоль — `mode=managed-redis-tls`, `status=connected`; секрет в
  ответах отсутствует.
- Документы: ШК-00-01 0.9.8, ШК-03-01 0.4, ШК-03-03 0.18, ШК-03-06 1.9,
  ШК-04-01 0.8, ШК-05-01 0.5, ШК-06-01 0.3, ШК-07-01 1.13, ШК-08-01 1.0,
  ШК-08-02 0.8, журнал 3.1, риски 0.4, ШК-10-19 1.5.

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
1. Write-only endpoint/секрет и остальные параметры плана 11.3.1.
2. Production Redis: отдельный ACL, приватная сеть, резервирование и алерты.
3. RLS по `school_id`: контекст транзакции и политики для 78 таблиц; только
   с тестовой PostgreSQL.
4. i18n, UI уведомлений и заявок документов; mobile consent-flow и геолокация.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`.
