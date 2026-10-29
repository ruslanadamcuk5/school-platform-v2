"""Learning-content (LMS) schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    name_i18n: dict
    icon: str
    color: str
    description: str | None
    is_active: bool
    order_index: int


class MethodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    widget: str | None
    explanation: str | None
    steps: list
    example_key: str | None
    order_index: int


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    lesson_type: str
    status: str
    order_index: int


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    class_number: int
    code: str
    title: str
    title_i18n: dict
    description: str | None
    icon: str
    color: str
    part: int | None
    page_start: int | None
    page_end: int | None
    difficulty_level: int
    order_index: int
    source: str | None
    kind: str | None
    status: str


class TextbookLinkOut(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None
    pages: int | None
    file_id: uuid.UUID | None
    page_from: int | None
    page_to: int | None


class TopicDetailOut(TopicOut):
    methods: list[MethodOut] = []
    lessons: list[LessonOut] = []
    textbooks: list[TextbookLinkOut] = []


class TopicList(BaseModel):
    items: list[TopicOut]
    total: int
    limit: int
    offset: int


class TextbookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    class_number: int
    title: str
    author: str | None
    publisher: str | None
    year: str | None
    description: str | None
    pages: int | None
    file_id: uuid.UUID | None
    status: str
    created_at: datetime


class TextbookTopicOut(BaseModel):
    topic_id: uuid.UUID
    topic_code: str
    topic_title: str
    page_from: int | None
    page_to: int | None


class TextbookDetailOut(TextbookOut):
    topics: list[TextbookTopicOut] = []


class TextbookList(BaseModel):
    items: list[TextbookOut]
    total: int
    limit: int
    offset: int


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    description: str | None
    grade: int
    teacher_id: uuid.UUID
    school_id: uuid.UUID | None
    is_active: bool


class CourseTopicOut(BaseModel):
    topic_id: uuid.UUID
    code: str
    title: str
    order_index: int
    enabled: bool


class CourseClassOut(BaseModel):
    class_id: uuid.UUID
    title: str | None
    grade: int
    letter: str


class CourseDetailOut(CourseOut):
    topics: list[CourseTopicOut] = []
    classes: list[CourseClassOut] = []
