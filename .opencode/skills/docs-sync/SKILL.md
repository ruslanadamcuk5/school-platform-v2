---
name: docs-sync
description: Обновить только те документы, которых касается изменение, и зафиксировать его в журнале
---

## Когда использовать
После изменения API, схемы БД, безопасности, версии или пилота.

## Матрица
| Изменение | Документы |
|---|---|
| API | `docs/03-architecture/03-api.md`, журнал |
| Схема БД | `docs/04-data/01-model-dannyh.md`, миграция, журнал |
| Права/сервисы | `docs/03-architecture/05-gruppy-i-prava.md`, `docs/04-data/02-model-grupp-prav-i-servisov.md`, журнал |
| Безопасность/ПДн | `docs/05-security/01-koncepciya-ib.md`, журнал |
| Версия | `backend/app/core/config.py`, `frontend/package.json`, `README.md`, `docs/README.md`, реестр, `scripts/generate_docs.py`, журнал |
| Пилот | `docs/07-operations/01-razvertyvanie-i-ekspluataciya.md`, журнал |
| Тесты | отчёт в `docs/10-reporting/`, реестр |

## Порядок
1. Найди документ через `docs/INDEX.md`; читай только нужный раздел.
2. Внеси изменение и обнови версию/дату документа, если нужно.
3. Добавь запись в `docs/10-reporting/04-zhurnal-izmeneniy.md`.
4. Если добавлен новый документ — обнови реестр и запусти
   `python scripts/gen_docs_index.py`.
5. DOCX пересобирай только по команде, в фоне.

## Запреты
- Не переписывать весь документ из-за одной правки.
- Не менять юридически значимые формулировки без согласования.
