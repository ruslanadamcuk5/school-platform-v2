---
description: Подготовить релиз версии без деплоя
---

Подготовь релиз версии `$ARGUMENTS`.

1. Согласуй версию, если она не указана.
2. Обнови версии в backend, frontend, README, docs/README, реестре и
   `scripts/generate_docs.py`.
3. Запусти `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1`.
4. Перегенерируй `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/api/ENDPOINTS.md`.
5. Добавь запись в журнал изменений.
6. DOCX — только в фоне; покажи итог: число файлов и имя объединённого.
7. Не деплой.
