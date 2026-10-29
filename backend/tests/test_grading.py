"""Unit tests for assessment auto-grading rules."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.grading import (
    answer_detail,
    expected_text,
    grade_for_percent,
    is_answer_correct,
    normalize,
    summarize,
)


def _question(
    *,
    question_type: str = "single_choice",
    payload: dict | None = None,
    options: list[SimpleNamespace] | None = None,
    points: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        prompt="Вопрос",
        question_type=question_type,
        payload=payload or {},
        points=points,
        options=options or [],
    )


def _option(text: str, *, correct: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        option_text=text,
        is_correct=correct,
        order_index=0,
    )


def test_normalize_handles_whitespace_case_and_yo() -> None:
    assert normalize("  Ёлка \n") == "елка"
    assert normalize({"answer": " 42 "}) == "42"


def test_single_choice_accepts_text_and_option_id() -> None:
    correct = _option("4", correct=True)
    wrong = _option("5")
    question = _question(options=[correct, wrong])

    assert is_answer_correct(question, "4")
    assert is_answer_correct(question, str(correct.id))
    assert not is_answer_correct(question, "5")
    assert not is_answer_correct(question, "")


def test_multiple_choice_requires_all_correct_options() -> None:
    first = _option("красный", correct=True)
    second = _option("синий", correct=True)
    third = _option("зелёный")
    question = _question(
        question_type="multiple_choice", options=[first, second, third]
    )

    assert is_answer_correct(question, ["красный", "синий"])
    assert not is_answer_correct(question, ["красный"])
    assert not is_answer_correct(question, ["красный", "зелёный"])


def test_text_and_number_answers_use_payload() -> None:
    question = _question(
        question_type="number", payload={"answer": "3,5"}, points=2
    )

    assert is_answer_correct(question, "3,5")
    assert is_answer_correct(question, "3.5")
    assert not is_answer_correct(question, "3,6")
    detail = answer_detail(question, "3,5")
    assert detail["correct"] is True
    assert detail["points"] == 2
    assert detail["question_id"] == str(question.id)


def test_fraction_mixed_number_and_time_answers() -> None:
    fraction = _question(
        question_type="number",
        payload={"answer": "1/2", "answer_type": "fraction"},
    )
    mixed = _question(
        question_type="number",
        payload={"answer": "2 1/2", "answer_type": "mixed"},
    )
    time_task = _question(
        question_type="text",
        payload={"answer": "3:05", "answer_type": "time"},
    )

    assert is_answer_correct(fraction, "0,5")
    assert is_answer_correct(fraction, "1/2")
    assert is_answer_correct(mixed, "2,5")
    assert is_answer_correct(time_task, "3.05")
    assert is_answer_correct(time_task, "305")
    assert not is_answer_correct(time_task, "3:50")


def test_read_task_is_credited_on_submission() -> None:
    question = _question(question_type="read", payload={"task_type": "read"})

    assert is_answer_correct(question, "")
    assert expected_text(question) == "тема прочитана"


def test_dictation_uses_similarity_threshold() -> None:
    question = _question(
        question_type="text",
        payload={
            "task_type": "dictation",
            "reference_text": "Мама мыла раму",
            "answer": "Мама мыла раму",
        },
    )

    assert is_answer_correct(question, "мама мыла раму")
    assert is_answer_correct(question, "Мама мыла раму.")
    assert not is_answer_correct(question, "Совсем другой текст")


def test_grade_scale_and_summary() -> None:
    assert grade_for_percent(100) == 10
    assert grade_for_percent(90) == 10
    assert grade_for_percent(89) == 9
    assert grade_for_percent(60) == 7
    assert grade_for_percent(9) == 1
    assert summarize(2, 4) == (50, 6)
    assert summarize(0, 0) == (0, 1)
