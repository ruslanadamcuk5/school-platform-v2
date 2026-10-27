# Alwaysdata: пилотный контур

## 1. Что создаётся
- Отдельный сайт, не затрагивающий `virusadk.alwaysdata.net`.
- Отдельная база PostgreSQL.
- Отдельный пользователь БД.
- Отдельный каталог проекта.

## 2. Сайт
Тип сайта для FastAPI: **User program** (ASGI/Uvicorn).

Пример команды:
```bash
uvicorn app.main:app --host $IP --port $PORT --proxy-headers
```

Рабочая директория:
```text
/home/virusadk/school-platform-v2/backend
```

## 3. PostgreSQL
1. Открыть `Databases > PostgreSQL`.
2. Создать БД `school_platform`.
3. Создать пользователя `school_app`.
4. Выдать права только на эту БД.
5. Записать параметры подключения в `.env` (не в Git).
6. Проверить подключение:
```bash
psql "postgresql://school_app:***@***:5432/school_platform" -c "select 1;"
```

## 4. Переменные окружения
Задать в панели или в `.env` на сервере. Не коммитить.

## 5. Деплой
```bash
cd /home/virusadk/school-platform-v2
git pull
source /home/virusadk/.virtualenvs/school-platform/bin/activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
```
Затем перезапустить процесс сайта в панели.

## 6. Проверка
- `GET /health` → 200.
- `GET /docs` → OpenAPI.
- Логи процесса без ошибок.
- Подключение к БД и Redis.

## 7. Ограничения
- Это пилотный контур, не промышленный.
- Для аттестации и реальных ПДн нужен согласованный ЦОД.
- Внешние AI-сервисы включать только после оценки рисков.
