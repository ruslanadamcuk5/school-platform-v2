"""Analytics API schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsTotalsOut(BaseModel):
    students: int = 0
    teachers: int = 0
    classes: int = 0
    grades_count: int = 0


class AnalyticsGradesOut(BaseModel):
    average: float | None = None
    distribution: dict[int, int] = Field(default_factory=dict)
    excellent: int = 0
    good: int = 0
    satisfactory: int = 0
    low: int = 0


class AnalyticsAttendanceOut(BaseModel):
    total: int = 0
    present: int = 0
    absent: int = 0
    sick: int = 0
    late: int = 0
    excused: int = 0
    rate: float | None = None


class AnalyticsSubjectOut(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    grades_count: int = 0
    average: float | None = None
    attendance_total: int = 0
    attendance_rate: float | None = None


class AnalyticsClassOut(BaseModel):
    class_id: uuid.UUID
    class_name: str
    grade: int
    letter: str
    students: int = 0
    grades_count: int = 0
    average: float | None = None
    attendance_total: int = 0
    attendance_rate: float | None = None


class AnalyticsOverviewOut(BaseModel):
    school_id: uuid.UUID
    school_name: str
    academic_year: str
    available_years: list[str] = Field(default_factory=list)
    generated_at: datetime
    totals: AnalyticsTotalsOut
    grades: AnalyticsGradesOut
    attendance: AnalyticsAttendanceOut
    subjects: list[AnalyticsSubjectOut] = Field(default_factory=list)
    classes: list[AnalyticsClassOut] = Field(default_factory=list)
