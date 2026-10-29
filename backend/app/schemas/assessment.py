"""Assessment schemas: quizzes, assignments, submissions and results."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnswerOptionIn(BaseModel):
    option_text: str = Field(min_length=1, max_length=4000)
    is_correct: bool = False


class QuestionIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    question_type: str = Field(
        default="single_choice",
        pattern="^(single_choice|multiple_choice|text|number|read)$",
    )
    points: int = Field(default=1, ge=1, le=100)
    order_index: int = Field(default=0, ge=0)
    options: list[AnswerOptionIn] = Field(default_factory=list)
    correct_answer: str | list[str] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    quiz_type: str = Field(default="test", max_length=32)
    subject_id: uuid.UUID | None = None
    class_number: int | None = Field(default=None, ge=1, le=11)
    school_id: uuid.UUID | None = Field(
        default=None, description="Required for superadmin; ignored for school users"
    )
    time_limit_seconds: int = Field(default=0, ge=0, le=86400)
    max_attempts: int = Field(default=1, ge=1, le=20)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    questions: list[QuestionIn] = Field(min_length=1, max_length=200)


class QuizUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")
    time_limit_seconds: int | None = Field(default=None, ge=0, le=86400)
    max_attempts: int | None = Field(default=None, ge=1, le=20)


class AnswerOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    option_text: str
    order_index: int


class AnswerOptionAdminOut(AnswerOptionOut):
    is_correct: bool = False


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    question_type: str
    points: int
    order_index: int
    payload: dict[str, Any] = Field(default_factory=dict)
    options: list[AnswerOptionAdminOut] = Field(default_factory=list)


class QuestionPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    question_type: str
    points: int
    order_index: int
    options: list[AnswerOptionOut] = Field(default_factory=list)


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    quiz_type: str
    subject_id: uuid.UUID | None
    class_number: int | None
    school_id: uuid.UUID | None
    created_by: uuid.UUID | None
    time_limit_seconds: int
    max_attempts: int
    status: str
    ai_generated: bool
    created_at: datetime
    updated_at: datetime
    question_count: int = 0


class QuizDetailOut(QuizOut):
    questions: list[QuestionOut] = Field(default_factory=list)


class AssignmentCreate(BaseModel):
    quiz_id: uuid.UUID
    school_id: uuid.UUID | None = Field(
        default=None, description="Required for superadmin; ignored for school users"
    )
    target_type: str = Field(default="class", pattern="^(class|student)$")
    class_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    due_at: datetime | None = None
    instructions: str | None = Field(default=None, max_length=8000)
    status: str = Field(default="published", pattern="^(draft|published|closed|archived)$")


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    assigned_by: uuid.UUID | None
    target_type: str
    target_id: uuid.UUID | None
    class_id: uuid.UUID | None
    student_id: uuid.UUID | None
    starts_at: datetime | None
    due_at: datetime | None
    instructions: str | None
    status: str
    created_at: datetime
    quiz_title: str | None = None
    subject_id: uuid.UUID | None = None
    class_number: int | None = None
    question_count: int = 0


class AssignmentListItem(AssignmentOut):
    submitted: bool = False
    overdue: bool = False
    result: "SubmissionResultOut | None" = None
    results: list["StudentResultOut"] = Field(default_factory=list)


class StudentAnswerIn(BaseModel):
    question_id: uuid.UUID
    answer: str | list[str] | dict[str, Any] | None = None


class SubmissionCreate(BaseModel):
    answers: list[StudentAnswerIn] = Field(default_factory=list)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    device_id: str | None = Field(default=None, max_length=128)
    operation_id: uuid.UUID | None = None


class AnswerDetail(BaseModel):
    question_id: uuid.UUID | None
    prompt: str
    given: str
    expected: str
    correct: bool
    points: int
    solution: str | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    attempt_no: int
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    score: float | None
    max_score: float | None
    duration_seconds: int | None
    ai_checked: bool
    teacher_checked: bool
    teacher_comment: str | None
    created_at: datetime


class SubmissionResultOut(SubmissionOut):
    percent: int = 0
    grade: int = 0
    late: bool = False
    details: list[AnswerDetail] = Field(default_factory=list)


class StudentResultOut(BaseModel):
    student_id: uuid.UUID
    student_name: str
    submission: SubmissionOut
    percent: int = 0
    grade: int = 0
    details: list[AnswerDetail] = Field(default_factory=list)


class AssignmentResultsOut(BaseModel):
    assignment: AssignmentOut
    results: list[StudentResultOut] = Field(default_factory=list)


class AssignmentDetailOut(AssignmentOut):
    questions: list[QuestionPublicOut] = Field(default_factory=list)
    submitted: bool = False
    result: SubmissionResultOut | None = None
    attempts_used: int = 0
    attempts_left: int = 0


AssignmentListItem.model_rebuild()
