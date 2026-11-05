"""Generate docs/INDEX.md from the Markdown documentation sources.

The index is intentionally small: it contains only metadata and paths. Agents
read it first, then open the relevant section of a single document.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "INDEX.md"
EXCLUDE_PARTS = {"word", "archive"}
EXCLUDE_FILES = {OUT, DOCS / "CODEMAP.md", DOCS / "api" / "ENDPOINTS.md"}

PATTERNS = {
    "code": re.compile(r"\|\s*Код документа\s*\|\s*([^|]+?)\s*\|"),
    "version": re.compile(r"\|\s*Версия\s*\|\s*([^|]+?)\s*\|"),
    "date": re.compile(r"\|\s*Дата\s*\|\s*([^|]+?)\s*\|"),
}
BOLD_PATTERNS = {
    "code": re.compile(r"^\*\*Код документа:\*\*\s*(.+)$", re.MULTILINE),
    "version": re.compile(r"^\*\*(?:Версия|Версия пакета):\*\*\s*(.+)$", re.MULTILINE),
    "date": re.compile(r"^\*\*Дата:\*\*\s*(.+)$", re.MULTILINE),
}


def _clean(value: str) -> str:
    return value.replace("|", r"\|").strip()


def parse_document(path: Path) -> dict[str, str | float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    title = path.stem
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    header_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            break
        header_lines.append(line)
    header = "\n".join(header_lines)
    values: dict[str, str | float] = {"title": title}
    for key, pattern in PATTERNS.items():
        match = pattern.search(header) or BOLD_PATTERNS[key].search(header)
        values[key] = match.group(1).strip() if match else ""
    values["size"] = path.stat().st_size / 1024
    return values


def main() -> None:
    rows: list[tuple[str, str, str, str, float, str]] = []
    for path in sorted(DOCS.rglob("*.md")):
        relative = path.relative_to(ROOT)
        if path in EXCLUDE_FILES or any(part in EXCLUDE_PARTS for part in relative.parts):
            continue
        info = parse_document(path)
        version = str(info["version"]).split()[0] if info["version"] else ""
        rows.append(
            (
                str(info["code"]),
                str(info["title"]),
                version,
                str(info["date"]),
                float(info["size"]),
                relative.as_posix(),
            )
        )

    rows.sort(key=lambda row: (row[0] or "Я", row[5]))
    lines = [
        "# Индекс документации",
        "",
        "> Сгенерировано `scripts/gen_docs_index.py`. Не редактировать вручную.",
        f"> Дата генерации: {date.today().strftime('%d.%m.%Y')}. Документов: {len(rows)}.",
        "",
        "## Как пользоваться",
        "1. Найдите документ по коду или названию.",
        "2. Читайте только нужный раздел, не весь файл.",
        "3. Для API используйте `docs/api/ENDPOINTS.md`, для кода — `docs/CODEMAP.md`.",
        "4. `docs/word/**` не читать: это сгенерированные DOCX.",
        "",
        "| Код | Документ | Версия | Дата | КБ | Путь |",
        "|---|---|---|---|---:|---|",
    ]
    for code, title, version, doc_date, size, relative in rows:
        lines.append(
            f"| {_clean(code)} | {_clean(title)} | {_clean(version)} | "
            f"{_clean(doc_date)} | {size:.1f} | `{relative}` |"
        )
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(rows)} documents)")


if __name__ == "__main__":
    main()
