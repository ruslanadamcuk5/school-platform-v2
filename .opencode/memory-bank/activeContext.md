# Active Context

## Текущий этап
**2.18. Безопасность и психологическая поддержка + 2.19. Экономия токенов.**
Дата: 2026-11-05. Версия API/frontend: `0.9.0`.

## Состояние
- Пилот: `0.9.0`; `/health` — `ok`; head `0010_safety`; backup
  `20261105T080100Z`; старый frontend — `dist.pre-0.9.0-20261105T080100Z`.
- `safety` на пилоте выключен: `default_enabled=false`, активаций нет.
- Локально: `safety` реализован; backend `184 passed`; Ruff чистый;
  OpenAPI `172` пути / `232` операции; frontend typecheck/build успешны.
- Safety: обращения (включая анонимные), инциденты, согласия, геолокация,
  настройки и очистка по срокам; 16 маршрутов.
- Документы: v0.9.0; деплой записан в ШК-07-01; журнал 1.6; отчёты
  ШК-10-19 (1.1) и ШК-10-20; DOCX собран — 47 отдельных файлов и
  объединённый `v0.9.0`.
- OpenCode: агрессивный пакет применён — `model=opencode/deepseek-v4.1-flash-free`;
  `browser*`/`opencode*` выключены, для UI есть `@browser`; подагенты
  `explorer`/`test-runner`/`docs-writer` на бесплатной модели; команды
  `/check`, `/test`, `/docs`, `/api`, `/release`, `/db-schema`, `/pilot-status`
  идут через `subtask`; bash-allowlist; `task`-ограничения; лимиты `steps`;
  read-deny секретов; расширенный watcher.
- `AGENTS.md` — 6,4 КБ; `progress.md` сжат, история в `archive/progress-2026.md`.
- OpenCode DB: V2-схема (`session_v2`, 50 миграций) против CLI `1.19.4` (V1);
  `opencode db/models` падают. Backup БД есть; destructive-действия не выполнялись.

## Инварианты
- Не трогать `C:\Users\adamrv\Documents\edu-math`, его БД и процессы.
- Не менять `virusadk.alwaysdata.net`.
- Не коммитить секреты, токены, пароли, реальные ПДн.
- Пилотные данные синтетические (`synthetic_pilot_2026`).
- `safety` на пилоте не активировать без отдельной команды.
- API-first; `school_id`; RBAC; аудит; professional features только
  `vocational`/`higher`.
- Любое изменение API — в `docs/10-reporting/04-zhurnal-izmeneniy.md`.

## Следующие задачи
1. UI безопасности: обращения, инциденты, согласия, настройки.
2. E2E Playwright, i18n, Redis-кеш прав, RLS; затем UI уведомлений/документов.
3. При необходимости согласовать OpenCode CLI с V2 (`opencode upgrade --major`).
4. После перезапуска OpenCode проверить полное скрытие browser-схем и снять
   контрольные метрики по ШК-10-20.

## Навигация
- `docs/INDEX.md` — документация; `docs/CODEMAP.md` — код;
  `docs/api/ENDPOINTS.md` — API.
- Полная история: `.opencode/memory-bank/archive/progress-2026.md`.
- Решения: `.opencode/memory-bank/decisions.md`.
- Глоссарий: `.opencode/memory-bank/glossary.md`.
- Git: `C:\Users\adamrv\AppData\Local\MinGit\cmd\git.exe`
  (или `git` после перезапуска терминала).
