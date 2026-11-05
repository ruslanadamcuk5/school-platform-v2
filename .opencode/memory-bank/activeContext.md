# Active Context

## Текущий этап
**2.18. Безопасность и психологическая поддержка.**
Дата: 2026-11-05. Версия API/frontend: `0.9.0`.

## Состояние
- Пилот: `0.8.3`; миграции `0006`–`0009`; backup `20261104T115542Z`; `/health` — `200`.
- Локально: `safety` реализован; head `0010_safety`; на пилот не выкачен.
- Backend: `184 passed`; Ruff чисто; OpenAPI 172 пути / 232 операции.
- Frontend: `typecheck` и production build успешны.
- Safety: обращения (включая анонимные), инциденты, согласия, геолокация,
  настройки и очистка по срокам; 16 маршрутов; настройки —
  `safety.settings` (глобально) и `safety.settings:{school_id}`.
- Документы: v0.9.0, DOCX собран, отчёт ШК-10-19, журнал 1.4.
- Инструменты: `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/api/ENDPOINTS.md`,
  skills/commands/subagents, `scripts/check.ps1`, Context7 MCP (ключ в User env).

## Инварианты
- Не трогать `C:\Users\adamrv\Documents\edu-math`, его БД и процессы.
- Не менять `virusadk.alwaysdata.net`.
- Не коммитить секреты, токены, пароли, реальные ПДн.
- Пилотные данные синтетические (`synthetic_pilot_2026`).
- Не применять `0010` и не деплоить `safety` без отдельной команды.
- API-first; `school_id`; RBAC; аудит; professional features только
  `vocational`/`higher`.
- Любое изменение API — в `docs/10-reporting/04-zhurnal-izmeneniy.md`.

## Следующие 3 задачи
1. По команде: применить `0010`, seed, доставить `safety`, активировать сервис.
2. UI безопасности: обращения, инциденты, согласия, настройки.
3. E2E Playwright, i18n, Redis-кеш прав, RLS; затем UI уведомлений/документов.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Глоссарий: `.opencode/memory-bank/glossary.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
