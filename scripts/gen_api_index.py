"""Generate docs/api/ENDPOINTS.md from the FastAPI OpenAPI schema.

Run from the ``backend`` directory (or any directory): the script changes into
``backend`` so that the application's relative ``.env`` handling keeps working.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = ROOT / "docs" / "api" / "ENDPOINTS.md"
METHODS = ("get", "post", "put", "patch", "delete", "options", "head")


def _clean(value: object) -> str:
    return str(value or "").replace("|", r"\|").strip()


def main() -> None:
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from app.main import app  # noqa: PLC0415

    spec = app.openapi()
    paths = spec.get("paths", {})
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for path, item in sorted(paths.items()):
        for method in METHODS:
            operation = item.get(method)
            if not operation:
                continue
            tags = operation.get("tags") or ["other"]
            tag = str(tags[0])
            summary = str(operation.get("summary") or "")
            if len(summary) > 120:
                summary = summary[:117] + "..."
            groups.setdefault(tag, []).append((method.upper(), path, summary))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    version = str(spec.get("info", {}).get("version") or "")
    operation_count = sum(len(items) for items in groups.values())
    lines = [
        "# Индекс эндпоинтов API",
        "",
        "> Сгенерировано `scripts/gen_api_index.py`. Не редактировать вручную.",
        f"> Дата генерации: {date.today().strftime('%d.%m.%Y')}.",
        f"> Версия OpenAPI: `{version}`. Путей: {len(paths)}; операций: {operation_count}.",
        "",
        "## Как пользоваться",
        "1. Найдите маршрут по тегу, пути или summary.",
        "2. Для деталей откройте `docs/03-architecture/03-api.md` или `/openapi.json`.",
        "3. Не читайте весь файл: используйте поиск по строке.",
        "",
    ]
    for tag in sorted(groups):
        lines.append(f"## {_clean(tag)}")
        for method, path, summary in groups[tag]:
            suffix = f" — {_clean(summary)}" if summary else ""
            lines.append(f"- `{method}` `{path}`{suffix}")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(
        f"Wrote {OUT.relative_to(ROOT)} "
        f"({len(paths)} paths, {operation_count} operations, version {version})"
    )


if __name__ == "__main__":
    main()
