---
description: Запустить точечные тесты pytest
---

Запусти точечные тесты для `$ARGUMENTS`:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -o addopts="" -q --tb=line -p no:warnings $ARGUMENTS
```

Покажи только падения и итоговую строку. Если аргумент не указан, запусти
`scripts/check.ps1`.
