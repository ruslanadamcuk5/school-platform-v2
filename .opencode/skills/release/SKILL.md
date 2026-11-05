---
name: release
description: Подготовить релиз платформы: версии, проверки, документация и DOCX, без деплоя
---

## Когда использовать
Перед сдачей этапа или публикацией версии.

## Порядок
1. Согласуй номер версии с пользователем.
2. Обнови версии:
   - `backend/app/core/config.py`;
   - `frontend/package.json` и `package-lock.json`;
   - `README.md`, `docs/README.md`;
   - `docs/00-register/01-register-dokumentacii.md`;
   - `scripts/generate_docs.py`;
   - запись в `docs/10-reporting/04-zhurnal-izmeneniy.md`.
3. Запусти `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1`.
4. Перегенерируй индексы:
   ```powershell
   .venv\Scripts\python.exe scripts\gen_docs_index.py
   .venv\Scripts\python.exe scripts\gen_codemap.py
   cd backend; ..\.venv\Scripts\python.exe ..\scripts\gen_api_index.py
   ```
5. DOCX — только по команде и в фоне:
   ```powershell
   .venv\Scripts\python.exe scripts\generate_docs.py
   ```
   В контекст — только итог: число файлов и имя объединённого.
6. Проверь `git status`, `git diff --stat`, отсутствие секретов.

## Запреты
- Не деплоить в рамках этого skill.
- Не коммитить `.env`, `secrets/`, реальные ПДн.
- Не менять API без записи в журнале.
