"""Journal schemas: schedule, grades and attendance."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

ATTENDANCE_PATTERN = "^(present|absent|sick|late|excused)$"


class ScheduleItemIn(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID | None = None
    day_of_week: int = Field(ge=1, le=7)
    lesson_no: int = Field(ge=1, le=12)
    start_time: time
    end_time: time
    room: str | None = Field(default=None, max_length=64)
    topic_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "ScheduleItemIn":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.valid_to is not None and self.valid_from is not None:
            if self.valid_to < self.valid_from:
                raise ValueError("valid_to must be on or after valid_from")
        return self


class ScheduleItemUpdate(BaseModel):
    class_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    day_of_week: int | None = Field(default=None, ge=1, le=7)
    lesson_no: int | None = Field(default=None, ge=1, le=12)
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=64)
    topic_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_to: date | None = None


class ScheduleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str | None = None
    subject_id: uuid.UUID
    subject_name: str | None = None
    subject_icon: str | None = None
    teacher_id: uuid.UUID | None
    teacher_name: str | None = None
    day_of_week: int
    lesson_no: int
    start_time: time
    end_time: time
    room: str | None
    topic_id: uuid.UUID | None
    topic_title: str | None = None
    note: str | None
    valid_from: date
    valid_to: date | None
    created_at: datetime


class ScheduleListOut(BaseModel):
    weekdays: list[str]
    schedule: list[ScheduleItemOut] = Field(default_factory=list)


class JournalClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grade: int
    letter: str
    display_name: str
    academic_year: str


class JournalStudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    login: str


class JournalEntryIn(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    student_id: uuid.UUID
    lesson_date: date
    lesson_topic: str | None = Field(default=None, max_length=255)
    grade: int | None = Field(default=None, ge=1, le=10)
    attendance: str = Field(default="present", pattern=ATTENDANCE_PATTERN)
    comment: str | None = Field(default=None, max_length=4000)


class JournalEntryUpdate(BaseModel):
    lesson_topic: str | None = Field(default=None, max_length=255)
    grade: int | None = Field(default=None, ge=1, le=10)
    attendance: str | None = Field(default=None, pattern=ATTENDANCE_PATTERN)
    comment: str | None = Field(default=None, max_length=4000)


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str | None = None
    subject_id: uuid.UUID
    subject_name: str | None = None
    teacher_id: uuid.UUID | None
    teacher_name: str | None = None
    student_id: uuid.UUID
    student_name: str | None = None
    lesson_date: date
    lesson_topic: str | None
    grade: int | None
    attendance: str
    comment: str | None
    created_at: datetime
    updated_at: datetime


class JournalBulkItem(BaseModel):
    student_id: uuid.UUID
    grade: int | None = Field(default=None, ge=1, le=10)
    attendance: str = Field(default="present", pattern=ATTENDANCE_PATTERN)
    comment: str | None = Field(default=None, max_length=4000)


class JournalBulkIn(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    lesson_date: date
    lesson_topic: str | None = Field(default=None, max_length=255)
    items: list[JournalBulkItem] = Field(min_length=1, max_length=100)


class JournalBulkOut(BaseModel):
    created: int = 0
    updated: int = 0
    entries: list[JournalEntryOut] = Field(default_factory=list)


class JournalSummaryOut(BaseModel):
    student_id: uuid.UUID
    student_name: str
    entries_count: int
    grades_count: int
    average_grade: float | None = None
    attendance: dict[str, int] = Field(default_factory=dict)
    grades: list[int] = Field(default_factory=list)


class JournalSummaryListOut(BaseModel):
    items: list[JournalSummaryOut] = Field(default_factory=list)


class StatusOut(BaseModel):
    status: str = "ok"
