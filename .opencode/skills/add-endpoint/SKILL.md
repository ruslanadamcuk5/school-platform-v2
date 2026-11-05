---
name: add-endpoint
description: Добавить защищённый эндпоинт FastAPI с проверкой права, school_id, аудитом, тестом и документацией
---

## Когда использовать
Новый маршрут в `backend/app/api/v1/`.

## Порядок
1. Прочитай `docs/CODEMAP.md` (раздел API), `backend/app/api/v1/router.py`
   и ближайший роутер того же домена.
2. Схемы — в `backend/app/schemas/<domain>.py`: Pydantic v2, валидаторы,
   JSONB-поля `{"ru": "...", "by": "...", "en": "..."}`.
3. Роутер — в `backend/app/api/v1/<domain>.py`:
   - `CurrentUser`, `SessionDep`;
   - `Depends(require_permission("<service>.<action>"))`;
   - `require_service("<service>")`, если сервис включается для школы;
   - `school_id` — из пользователя или payload, проверить принадлежность;
   - `add_audit_event(...)` для изменений;
   - `status_code` и `response_model`.
4. Новый роутер зарегистрируй в `backend/app/api/v1/router.py`.
5. Право добавь в `backend/app/services/registry.py`; legacy-мост —
   `backend/app/services/access.py`.
6. Тесты: `backend/tests/test_<domain>.py` + кейс в `test_module_access.py`
   (403 без права/сервиса).
7. Документация: `docs/03-architecture/03-api.md`; при схеме —
   `docs/04-data/01-model-dannyh.md`; запись в
   `docs/10-reporting/04-zhurnal-izmeneniy.md`.
8. Проверка: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1`;
   при необходимости — точечный pytest.

## Запреты
- Не менять поведение старого API без записи в журнале.
- Не коммитить секреты и реальные ПДн.
- Не читать `docs/word`, `node_modules`, `.venv`.
