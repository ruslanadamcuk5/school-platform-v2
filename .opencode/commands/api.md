---
description: Перегенерировать индекс эндпоинтов из OpenAPI
agent: build
subtask: true
---

Запусти:

```powershell
cd backend
..\.venv\Scripts\python.exe ..\scripts\gen_api_index.py
```

Покажи только версию OpenAPI, число путей и операций. Не читай весь
`docs/api/ENDPOINTS.md`.
