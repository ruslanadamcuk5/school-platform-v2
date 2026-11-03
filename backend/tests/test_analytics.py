"""Tests for analytics report helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.api.v1.analytics import _average, _csv_cell, _percent, build_class_csv
from app.schemas.analytics import (
    AnalyticsAttendanceOut,
    AnalyticsClassOut,
    AnalyticsGradesOut,
    AnalyticsOverviewOut,
    AnalyticsTotalsOut,
)


def _overview() -> AnalyticsOverviewOut:
    return AnalyticsOverviewOut(
        school_id=uuid.uuid4(),
        school_name='Пилотная школа "ВЕКТОР"',
        academic_year="2026/2027",
        available_years=["2026/2027"],
        generated_at=datetime.now(timezone.utc),
        totals=AnalyticsTotalsOut(students=24, teachers=8, classes=2, grades_count=10),
        grades=AnalyticsGradesOut(average=7.5),
        attendance=AnalyticsAttendanceOut(total=30, present=24, late=2, rate=86.7),
        classes=[
            AnalyticsClassOut(
                class_id=uuid.uuid4(),
                class_name="5,А",
                grade=5,
                letter="А",
                students=12,
                grades_count=6,
                average=7.25,
                attendance_total=18,
                attendance_rate=88.9,
            )
        ],
    )


def test_percent_handles_empty_and_rounds() -> None:
    assert _percent(0, 0) is None
    assert _percent(2, 3) == 66.7
    assert _percent(15, 15) == 100.0


def test_average_is_rounded_and_keeps_empty() -> None:
    assert _average(None) is None
    assert _average(7.254) == 7.25


def test_csv_cell_quotes_special_values() -> None:
    assert _csv_cell("5А") == "5А"
    assert _csv_cell("5,А") == '"5,А"'
    assert _csv_cell('школа "Пилот"') == '"школа ""Пилот"""'


def test_class_csv_contains_header_and_rows() -> None:
    payload = build_class_csv(_overview())
    assert "Учебный год,2026/2027" in payload
    assert 'Класс,Учеников,Оценок,Средний балл,"Посещаемость, %"' in payload
    assert '"5,А",12,6,7.25,88.9' in payload
