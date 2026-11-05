"""Generate docs/CODEMAP.md: a compact map of modules and top-level symbols.

The map is a navigation aid, not a replacement for reading source files. It is
small enough to scan and points to exact files and line numbers.
"""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CODEMAP.md"
EXCLUDE_PARTS = {".venv", "node_modules", "__pycache__", "dist", "build", ".git"}

TS_EXPORT = re.compile(
    r"^export\s+(?:async\s+)?(?:function|class|interface|type|const|enum)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
PY_TEST = re.compile(r"^\s*(?:async\s+)?def\s+test_[A-Za-z0-9_]+", re.MULTILINE)


def _iter_files(base: Path, suffixes: tuple[str, ...]):
    for path in sorted(base.rglob("*")):
        if path.suffix not in suffixes or not path.is_file():
            continue
        if any(part in EXCLUDE_PARTS for part in path.parts):
            continue
        yield path


def _limit(items: list[str], max_items: int = 10) -> str:
    if not items:
        return "—"
    if len(items) <= max_items:
        return ", ".join(items)
    return ", ".join(items[:max_items]) + f" (+{len(items) - max_items})"


def python_symbols(path: Path) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return [], []
    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(f"{node.name}:{node.lineno}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(f"{node.name}:{node.lineno}")
    return classes, functions


def ts_symbols(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return TS_EXPORT.findall(text)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    backend_files = list(_iter_files(ROOT / "backend" / "app", (".py",)))
    test_files = list(_iter_files(ROOT / "backend" / "tests", (".py",)))
    frontend_files = list(_iter_files(ROOT / "frontend" / "src", (".ts", ".tsx")))

    lines = [
        "# Карта кода",
        "",
        "> Сгенерировано `scripts/gen_codemap.py`. Не редактировать вручную.",
        f"> Дата генерации: {date.today().strftime('%d.%m.%Y')}.",
        f"> Backend: {len(backend_files)} файлов; tests: {len(test_files)}; "
        f"frontend: {len(frontend_files)}.",
        "",
        "## Как пользоваться",
        "1. Найдите домен в таблице.",
        "2. Откройте 1–2 файла по указанному пути, не весь каталог.",
        "3. Для маршрутов API используйте `docs/api/ENDPOINTS.md`.",
        "",
        "## Backend",
        "| Файл | Строк | Классы | Функции |",
        "|---|---:|---|---|",
    ]
    for path in backend_files:
        classes, functions = python_symbols(path)
        line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        lines.append(
            f"| `{relative(path)}` | {line_count} | {_limit(classes)} | "
            f"{_limit(functions)} |"
        )

    lines.extend(
        [
            "",
            "## Frontend",
            "| Файл | Строк | Экспорты |",
            "|---|---:|---|",
        ]
    )
    for path in frontend_files:
        exports = ts_symbols(path)
        line_count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        lines.append(f"| `{relative(path)}` | {line_count} | {_limit(exports)} |")

    lines.extend(
        [
            "",
            "## Tests",
            "| Файл | Строк | Тестов |",
            "|---|---:|---:|",
        ]
    )
    for path in test_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        count = len(PY_TEST.findall(text))
        lines.append(f"| `{relative(path)}` | {len(text.splitlines())} | {count} |")

    lines.extend(
        [
            "",
            "## Где искать",
            "- API-роутеры: `backend/app/api/v1/`.",
            "- Сервисы и права: `backend/app/services/`.",
            "- Модели: `backend/app/models/`; схемы: `backend/app/schemas/`.",
            "- Миграции: `backend/alembic/versions/`.",
            "- Веб-клиент: `frontend/src/pages/`, `frontend/src/api/`, `frontend/src/components/`.",
            "- Документация: `docs/INDEX.md`.",
            "",
        ]
    )
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
