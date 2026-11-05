---
name: test-triage
description: Запустить точечные тесты и разобрать падения с минимальным выводом
---

## Когда использовать
После изменения кода или при красном CI.

## Порядок
1. Сначала точечно:
   ```powershell
   cd backend
   ..\.venv\Scripts\python.exe -m pytest -o addopts="" -q --tb=line -p no:warnings tests/test_<domain>.py
   ```
2. Если нужно — только упавшие:
   ```powershell
   ..\.venv\Scripts\python.exe -m pytest -o addopts="" -q --lf --tb=line -p no:warnings
   ```
3. Полная проверка (из каталога `backend`):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File ..\scripts\check.ps1
   ```
4. Читай только строки ошибок и релевантный код; не весь лог.
5. Исправь причину, повтори точечный тест, затем полный.

## Запреты
- Не отключать тесты и не ослаблять проверки без записи в журнале.
- Не показывать в ответе весь вывод pytest.
