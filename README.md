# ЕООП «Школьник» — school-platform-v2

Новая версия единой общеобразовательной обучающей платформы для Республики
Беларусь. Проект создаётся как преемник работающего Flask/SQLite-приложения:
существующий функционал переносится поэтапно, без остановки текущего сервиса.

## Текущий статус
**Этап 0 — инициализация.** Создана структура проекта, документация, правила
OpenCode, заготовки инфраструктуры. Прикладной код ещё не переносился.

## Целевой стек
- Backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis.
- Web: React + TypeScript + Vite + TailwindCSS.
- Mobile: Flutter (Android/iOS).
- AI: OpenRouter / DeepSeek.
- Файлы: S3-совместимое хранилище.

## Структура
```text
school-platform-v2/
├── opencode.json
├── AGENTS.md
├── .opencode/memory-bank/     # память агента между сессиями
├── backend/                   # FastAPI
├── frontend/                  # React
├── docs/                      # проектная документация (MD + DOCX)
├── deploy/alwaysdata/         # инструкции и конфигурация хостинга
└── scripts/                   # генерация документации и служебные скрипты
```

## Быстрый старт
1. Установить Python 3.12+ и PostgreSQL 16+ (или использовать managed PostgreSQL).
2. Создать виртуальное окружение: `python -m venv .venv`.
3. Активировать: `.venv\Scripts\Activate.ps1`.
4. Установить зависимости backend: `pip install -r backend/requirements.txt`
   (файл появится на этапе 1).
5. Скопировать `.env.example` в `.env` и заполнить значения.
6. Запустить инфраструктуру: `docker compose up -d` (если установлен Docker).
7. Запустить API: `uvicorn app.main:app --reload` из `backend/`.

## Документация
- [Реестр документов](docs/00-register/01-register-dokumentacii.md)
- [Концепция](docs/01-concept/01-koncepciya.md)
- [Техническое задание](docs/02-tz/01-tehnicheskoe-zadanie.md)
- [Функции по ролям](docs/02-tz/02-funkcionalnye-trebovaniya-po-rolyam.md)
- [Архитектура](docs/03-architecture/01-arhitektura.md)
- [Модель данных](docs/04-data/01-model-dannyh.md)
- [Безопасность](docs/05-security/01-koncepciya-ib.md)
- [План разработки](docs/08-roadmap/01-plan-razrabotki.md)
- [Нормативные документы](docs/09-normative/01-reestr-normativnyh-dokumentov.md)

## Правила работы
Основные правила для разработчика и AI-агента — в [AGENTS.md](AGENTS.md).
Перед каждой сессией OpenCode читает `.opencode/memory-bank/activeContext.md`.
