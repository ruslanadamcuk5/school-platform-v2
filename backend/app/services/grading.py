"""Auto-grading helpers for assessment submissions.

The legacy Flask application stored a JSON task list together with each
assignment. The new schema keeps the same information in ``questions``,
``answer_options`` and ``questions.payload``, so the rules below support both
imported and newly created quizzes.

Normalization follows the old ``content.answer`` module: decimal commas,
fractions, mixed numbers, units, dashes and superscripts are handled.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.models.assessment import Question

SUPERSCRIPT = str.maketrans({"²": "2", "³": "3"})
UNIT_RE = re.compile(
    r"(руб|р\.|р\b|коп|коп\.|шт|см|м|кг|г|мин|ч|км|см2|см²|кв\.?\s*см|"
    r"см3|см³|м2|м²|км2|км²|га)"
)
PUNCT_RE = re.compile(r"[!\"#$%&'()*+,:;<=>?@\[\\\]^_`{|}~]")


def _clean(text: Any) -> str:
    text = unicodedata.normalize("NFKC", str(text or ""))
    return text.translate(SUPERSCRIPT).strip().lower().replace("ё", "е")


def normalize_text(text: Any) -> str:
    """Canonical text form used for choice and text answers."""
    value = _clean(text).replace(",", ".")
    value = value.replace("−", "-").replace("–", "-")
    value = UNIT_RE.sub("", value)
    value = PUNCT_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_number(text: Any) -> float | None:
    """Parse an integer, decimal, fraction or mixed number."""
    raw = _clean(text).replace(",", ".").replace("−", "-")
    raw = re.sub(r"(руб|р\.|р\b|коп|коп\.|шт|см|м|кг|г|мин|ч|км)", "", raw).strip()
    if not raw:
        return None

    match = re.fullmatch(r"(-?\d+)\s+(\d+)\s*/\s*(\d+(?:\.\d+)?)", raw)
    if match:
        whole, numerator, denominator = (
            int(match.group(1)),
            int(match.group(2)),
            float(match.group(3)),
        )
        if denominator:
            sign = -1 if whole < 0 else 1
            return sign * (abs(whole) + numerator / denominator)

    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)", raw)
    if match:
        numerator, denominator = float(match.group(1)), float(match.group(2))
        return numerator / denominator if denominator else None

    raw = raw.replace(" ", "")
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", raw)
    if match:
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def normalize_time(text: Any) -> str | None:
    """Convert ``3:05``, ``3.05``, ``305`` and ``3 05`` to ``3:05``."""
    value = _clean(text).replace(".", ":").replace(",", ":")
    value = re.sub(r"[^\d:]", "", value)
    if not value:
        return None
    if ":" in value:
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            return None
        hours, minutes = int(parts[0]), int(parts[1])
    else:
        if len(value) == 3:
            hours, minutes = int(value[0]), int(value[1:])
        elif len(value) == 4:
            hours, minutes = int(value[:2]), int(value[2:])
        elif len(value) in (1, 2):
            hours, minutes = int(value), 0
        else:
            return None
    if minutes > 59:
        return None
    return f"{hours}:{minutes:02d}"


def normalize(value: Any) -> str:
    """Normalize a free-form answer, unwrapping the old client's dict shape."""
    if isinstance(value, dict):
        for key in ("answer", "value", "given", "text", "option_id"):
            if key in value:
                return normalize(value[key])
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return normalize_text(value)


def _given_values(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value if normalize(item)]
    text = normalize(value)
    return [text] if text else []


def _payload_answer(question: Question) -> Any:
    payload = question.payload or {}
    return payload.get("answer", payload.get("correct_answer"))


def _answer_type(question: Question) -> str:
    payload = question.payload or {}
    kind = str(payload.get("answer_type") or "").lower()
    if kind:
        return kind
    return {
        "single_choice": "choice",
        "multiple_choice": "choice",
        "number": "number",
        "read": "read",
        "text": "text",
    }.get(question.question_type, "text")


def _read_task(question: Question) -> bool:
    payload = question.payload or {}
    return _answer_type(question) == "read" or normalize_text(
        payload.get("task_type")
    ) == "read"


def _correct_choices(question: Question) -> tuple[set[str], set[str]]:
    texts: set[str] = set()
    ids: set[str] = set()
    for option in question.options or []:
        if option.is_correct:
            texts.add(normalize_text(option.option_text))
            ids.add(normalize_text(str(option.id)))
    return texts, ids


def _equal_floats(left: float, right: float) -> bool:
    return abs(left - right) < 1e-6


def dictation_similarity(reference: Any, given: Any) -> int:
    """Approximate dictation score used when no teacher/AI review is available."""
    from difflib import SequenceMatcher

    left = normalize_text(reference)
    right = normalize_text(given)
    if not left or not right:
        return 0
    return max(0, min(100, round(SequenceMatcher(None, left, right).ratio() * 100)))


def _compare_payload(question: Question, given: Any) -> bool:
    payload = question.payload or {}
    expected = _payload_answer(question)
    if normalize_text(payload.get("task_type")) == "dictation":
        reference = payload.get("reference_text") or expected
        return dictation_similarity(reference, given_text(given)) >= 60
    if expected is None:
        return False
    if isinstance(expected, list):
        expected_values = {normalize_text(item) for item in expected if normalize_text(item)}
        givens = set(_given_values(given))
        if question.question_type == "multiple_choice":
            return givens == expected_values
        return bool(givens & expected_values)

    answer_type = _answer_type(question)
    if answer_type in {"number", "fraction", "mixed"}:
        given_number = normalize_number(given)
        expected_number = normalize_number(expected)
        if given_number is not None and expected_number is not None:
            return _equal_floats(given_number, expected_number)
    if answer_type == "time":
        given_time, expected_time = normalize_time(given), normalize_time(expected)
        return given_time is not None and given_time == expected_time

    normalized_given = normalize_text(given)
    normalized_expected = normalize_text(expected)
    if normalized_given and normalized_given == normalized_expected:
        return True
    for alternative in payload.get("accept") or []:
        if normalized_given and normalized_given == normalize_text(alternative):
            return True
    return False


def is_answer_correct(question: Question, given: Any) -> bool:
    if _read_task(question):
        return True

    givens = _given_values(given)
    if not givens:
        return False

    correct_texts, correct_ids = _correct_choices(question)
    if correct_texts or correct_ids:
        matched_texts = {value for value in givens if value in correct_texts}
        matched_ids = {value for value in givens if value in correct_ids}
        if question.question_type == "multiple_choice":
            texts_ok = bool(correct_texts) and matched_texts == correct_texts
            ids_ok = bool(correct_ids) and matched_ids == correct_ids
            return texts_ok or ids_ok
        return bool(matched_texts or matched_ids)

    return _compare_payload(question, given)


def expected_text(question: Question) -> str:
    if _read_task(question):
        return "тема прочитана"
    correct_texts, _ = _correct_choices(question)
    if correct_texts:
        return "; ".join(sorted(correct_texts))
    expected = _payload_answer(question)
    if isinstance(expected, list):
        return "; ".join(str(item) for item in expected)
    if expected is None:
        return ""
    value = str(expected)
    if _answer_type(question) == "fraction":
        return value.replace("/", " / ")
    return value


def given_text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def answer_detail(question: Question, given: Any) -> dict[str, Any]:
    payload = question.payload or {}
    return {
        "question_id": str(question.id),
        "prompt": question.prompt,
        "given": given_text(given),
        "expected": expected_text(question),
        "correct": is_answer_correct(question, given),
        "points": question.points,
        "solution": payload.get("solution"),
    }


def grade_for_percent(percent: int) -> int:
    """Belarusian 10-point scale used by the legacy application."""
    if percent >= 90:
        return 10
    if percent >= 80:
        return 9
    if percent >= 70:
        return 8
    if percent >= 60:
        return 7
    if percent >= 50:
        return 6
    if percent >= 40:
        return 5
    if percent >= 30:
        return 4
    if percent >= 20:
        return 3
    if percent >= 10:
        return 2
    return 1


def summarize(score: float, max_score: float) -> tuple[int, int]:
    percent = round(score / max_score * 100) if max_score else 0
    return percent, grade_for_percent(percent)
