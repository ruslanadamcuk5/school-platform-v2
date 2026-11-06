# Active Context

## Текущий этап
**2.18 safety — завершён; 2.19 OpenCode — завершён; стабилизация 0.9.0.**
Дата: 2026-11-06. API/frontend: `0.9.0`.

## Состояние
- Пилот: `/health` — `ok`, `database=ok`, `jwt_ready=true`; head `0010_safety`.
- Safety UI: `dist` с `index-BaAbEN3E.js`, `index-BNJdgJYo.css`, `favicon.svg`;
  прежний — `dist.pre-vite8-20261105T133933Z`; UI под school_admin: 6 вкладок,
  геолокация off, консоль/сеть чисто.
- `safety` включён: school-активация `pilot-school`; `/me/services` —
  `enabled=true`, `source=activation`; 365/1095 дней, порог 16, анонимность on,
  `geolocation_enabled=false` до юррешения и mobile consent-flow.
- Backup активации: `20261105T103431Z-safety-activation` (дамп, dist, настройки).
- Restore-drill: временный PG 17.11, `RESTORE_EXIT=0` за 6,1 с; 78 таблиц /
  14 схем; `alembic=0010_safety`; users=217, audit=99; без `pgvector`.
- Frontend: React Router `7.18.5`, Vite `8.3.6`, Vitest `5.1.0`; Playwright E2E
  4 passed; Vitest 4; typecheck и build ok; `npm audit` — 0 (prod + dev).
- Backend: 193 passed; Ruff чистый; OpenAPI 172 пути / 232 операции.
- Redis: managed Upstash TLS подключён на пилоте; `REDIS_URL` в `.env` (600),
  backup `20261106T062733Z-upstash-redis`; restart master 2931184;
  `cache_ping=true`, `connected_clients=2`, версия ключа создана.
  Локально 8.10.3, 9 тестов кеша.
- Документы: ШК-03-01 0.4, ШК-03-06 1.8, ШК-05-01 0.4, ШК-06-01 0.3,
  ШК-07-01 1.6, ШК-08-01 0.7, ШК-08-02 0.5, журнал 2.4, ШК-10-19 1.5.
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
1. Сменить пароль Upstash (был передан в чате), обновить `.env` и перезапустить.
2. Реализовать админ-консоль эксплуатационных настроек (план 11.3.1): кеш,
   лимиты, режим обслуживания, интеграции, health-пороги, аудит и маскирование.
3. Production Redis: отдельный ACL, приватная сеть, резервирование и алерты.
4. RLS по `school_id`: контекст транзакции и политики для 78 таблиц; только
   с тестовой PostgreSQL.
5. i18n, UI уведомлений и заявок документов; mobile consent-flow и геолокация.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
