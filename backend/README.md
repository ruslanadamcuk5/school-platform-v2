# Backend (FastAPI)

Каталог для нового backend. Прикладной код появится после анализа текущего
Flask-проекта и утверждения карты миграции.

## Планируемая структура
```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   ├── domains/
│   │   ├── iam/
│   │   ├── org/
│   │   ├── lms/
│   │   ├── assessment/
│   │   ├── journal/
│   │   ├── communication/
│   │   ├── safety/
│   │   ├── documents/
│   │   ├── analytics/
│   │   └── ai/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── workers/
├── alembic/
├── tests/
├── requirements.txt
└── Dockerfile
```

## Правила
- Только async SQLAlchemy и asyncpg.
- Pydantic v2.
- Все миграции — Alembic.
- Каждый эндпоинт покрывается тестами.
- Секреты — только через переменные окружения.
