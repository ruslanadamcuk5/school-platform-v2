"""Library schemas: books, class access and recommendations."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.lms import SubjectOut


class LibraryTopicOut(BaseModel):
    topic_id: uuid.UUID
    code: str
    title: str
    icon: str
    class_number: int
    page_from: int | None = None
    page_to: int | None = None


class LibraryBookOut(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None
    description: str | None
    class_number: int | None
    subject_id: uuid.UUID | None
    subject_name: str | None = None
    subject_icon: str | None = None
    textbook_id: uuid.UUID | None
    textbook_title: str | None = None
    pages: int | None = None
    topics_count: int = 0
    classes_count: int = 0
    owner_id: uuid.UUID | None
    owner_name: str | None = None
    class_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime


class LibraryRecommendationOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    book_title: str | None = None
    topic_id: uuid.UUID | None
    topic_title: str | None = None
    teacher_id: uuid.UUID
    teacher_name: str | None = None
    target_type: str
    class_id: uuid.UUID | None
    class_name: str | None = None
    student_id: uuid.UUID | None
    student_name: str | None = None
    note: str | None
    created_at: datetime
    done: bool = False
    done_at: datetime | None = None
    done_count: int = 0
    total_count: int = 0


class LibraryBookDetailOut(LibraryBookOut):
    topics: list[LibraryTopicOut] = Field(default_factory=list)
    recommendations: list[LibraryRecommendationOut] = Field(default_factory=list)
    manageable: bool = False


class LibraryBookCreate(BaseModel):
    textbook_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    class_number: int | None = Field(default=None, ge=1, le=11)
    title: str | None = Field(default=None, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    class_ids: list[uuid.UUID] = Field(default_factory=list)


class LibraryBookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    subject_id: uuid.UUID | None = None
    class_number: int | None = Field(default=None, ge=1, le=11)
    class_ids: list[uuid.UUID] | None = None


class LibraryRecommendationCreate(BaseModel):
    class_ids: list[uuid.UUID] = Field(default_factory=list)
    student_ids: list[uuid.UUID] = Field(default_factory=list)
    topic_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_targets(self) -> "LibraryRecommendationCreate":
        if not self.class_ids and not self.student_ids:
            raise ValueError("class_ids or student_ids is required")
        return self


class LibraryStatsOut(BaseModel):
    books: int = 0
    classes: int = 0
    recommendations: int = 0
    active: int = 0
    done: int = 0


class LibraryClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grade: int
    letter: str
    display_name: str
    academic_year: str


class LibraryChildOut(BaseModel):
    id: uuid.UUID
    full_name: str
    login: str


class LibraryStudentOut(BaseModel):
    id: uuid.UUID
    full_name: str
    login: str
    class_id: uuid.UUID
    class_name: str


class LibraryOut(BaseModel):
    books: list[LibraryBookOut] = Field(default_factory=list)
    recommendations: list[LibraryRecommendationOut] = Field(default_factory=list)
    stats: LibraryStatsOut = Field(default_factory=LibraryStatsOut)
    children: list[LibraryChildOut] = Field(default_factory=list)
    child: LibraryChildOut | None = None


class LibraryManageOut(BaseModel):
    books: list[LibraryBookOut] = Field(default_factory=list)
    stats: LibraryStatsOut = Field(default_factory=LibraryStatsOut)
    classes: list[LibraryClassOut] = Field(default_factory=list)
    students: list[LibraryStudentOut] = Field(default_factory=list)
    subjects: list[SubjectOut] = Field(default_factory=list)


class LibraryRecommendationListOut(BaseModel):
    items: list[LibraryRecommendationOut] = Field(default_factory=list)


class LibraryRecommendResult(BaseModel):
    created: int = 0
    skipped: int = 0
    items: list[LibraryRecommendationOut] = Field(default_factory=list)


class LibraryCatalogTopicOut(BaseModel):
    topic_id: uuid.UUID
    code: str
    title: str
    icon: str
    class_number: int
    page_from: int | None = None
    page_to: int | None = None


class LibraryCatalogItemOut(BaseModel):
    textbook_id: uuid.UUID
    book_id: uuid.UUID | None = None
    title: str
    author: str | None
    class_number: int
    subject_id: uuid.UUID
    subject_name: str | None = None
    subject_icon: str | None = None
    topics: list[LibraryCatalogTopicOut] = Field(default_factory=list)


class LibraryCatalogOut(BaseModel):
    items: list[LibraryCatalogItemOut] = Field(default_factory=list)


class LibraryStatusOut(BaseModel):
    status: str = "ok"
