# Active Context

## Текущий этап
**Этап 0. Инициализация проекта — завершён.**
Дата: 2026-10-27.

## Что сделано
1. Создана структура `C:\Users\adamrv\Documents\school-platform-v2`.
2. Настроены `opencode.json`, `AGENTS.md`, memory bank.
3. Подготовлен пакет проектной документации в `docs/` (Markdown + Word).
4. Создан GitHub-репозиторий `newvirusadk-cmd/school-platform-v2` (private)
   и выполнен push ветки `main`.
5. Создана отдельная PostgreSQL-база на Alwaysdata:
   `virusadk_school_platform` на `postgresql-virusadk.alwaysdata.net:5432`,
   пользователь `virusadk`, схемы и расширения настроены.
6. Создан отдельный пилотный сайт:
   `http://school-platform-v2.185.31.40.24.nip.io`.
   Сейчас это Static files со страницей-заглушкой из
   `deploy/alwaysdata/public/index.html`.
7. Локальные секреты вынесены в `.env` и `secrets/`, исключены из Git.
8. Проверено подключение к PostgreSQL (PostgreSQL 17.11).

## Что происходит сейчас
Ожидается выпуск автоматического SSL-сертификата Alwaysdata для
`school-platform-v2.185.31.40.24.nip.io`. После выпуска нужно включить
`Force HTTPS` и проверить сайт по HTTPS.

## Запреты
- Не трогать работающий проект `C:\Users\adamrv\Documents\edu-math`.
- Не менять его базу и не перезапускать его процессы.
- Не переносить реальные ПДн в новую систему без согласованной политики.
- Не коммитить `.env`, `secrets/`, пароли и приватные ключи.

## Следующая задача
Прочитать текущий Flask-проект `edu-math`, составить:
- перечень моделей и таблиц;
- перечень маршрутов и шаблонов;
- перечень функций по ролям;
- карту соответствия «старое → новое».

Результат записать в `docs/02-tz/05-karta-migracii.md`, обновить `progress.md`,
затем начать этап 1: FastAPI skeleton, healthcheck, SQLAlchemy, Alembic, JWT/RBAC.
