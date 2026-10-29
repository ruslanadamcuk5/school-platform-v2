"""Learning content: subjects, topics, methods, textbooks, courses and library."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.iam import User
    from app.models.org import School, SchoolClass


def _jsonb_object() -> Mapped[dict]:
    return mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class Subject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = {"schema": "lms"}

    code: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_i18n: Mapped[dict] = _jsonb_object()
    icon: Mapped[str] = mapped_column(
        String(32), nullable=False, default="📘", server_default="📘"
    )
    color: Mapped[str] = mapped_column(
        String(32), nullable=False, default="indigo", server_default="indigo"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    topics: Mapped[list["Topic"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    textbooks: Mapped[list["Textbook"]] = relationship(back_populates="subject")
    courses: Mapped[list["Course"]] = relationship(back_populates="subject")


class Topic(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("class_number BETWEEN 1 AND 11", name="class_number_range"),
        {"schema": "lms"},
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_i18n: Mapped[dict] = _jsonb_object()
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(
        String(32), nullable=False, default="📘", server_default="📘"
    )
    color: Mapped[str] = mapped_column(
        String(32), nullable=False, default="indigo", server_default="indigo"
    )
    part: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="active", server_default="active"
    )
    content: Mapped[list | dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    methods: Mapped[list["Method"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class Method(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "methods"
    __table_args__ = (
        UniqueConstraint("topic_id", "code", name="uq_methods_topic_code"),
        {"schema": "lms"},
    )

    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(CITEXT, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    widget: Mapped[str | None] = mapped_column(String(64), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    example_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    topic: Mapped["Topic"] = relationship(back_populates="methods")


class Lesson(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lessons"
    __table_args__ = {"schema": "lms"}

    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    lesson_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="text", server_default="text"
    )
    content: Mapped[dict] = _jsonb_object()
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft", server_default="draft"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    topic: Mapped["Topic"] = relationship(back_populates="lessons")
    blocks: Mapped[list["LessonBlock"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonBlock(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lesson_blocks"
    __table_args__ = {"schema": "lms"}

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = _jsonb_object()
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    lesson: Mapped["Lesson"] = relationship(back_populates="blocks")


class StoredFile(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "files"
    __table_args__ = {"schema": "lms"}

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(
        String(127), nullable=False, default="application/pdf",
        server_default="application/pdf",
    )
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    virus_scan_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Textbook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "textbooks"
    __table_args__ = {"schema": "lms"}

    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    class_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[str | None] = mapped_column(String(8), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="active", server_default="active"
    )

    subject: Mapped["Subject"] = relationship(back_populates="textbooks")
    file: Mapped["StoredFile | None"] = relationship()
    topic_links: Mapped[list["TextbookTopic"]] = relationship(
        back_populates="textbook", cascade="all, delete-orphan"
    )


class TextbookTopic(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "textbook_topics"
    __table_args__ = (
        UniqueConstraint(
            "textbook_id", "topic_id", name="uq_textbook_topics_textbook_topic"
        ),
        {"schema": "lms"},
    )

    textbook_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.textbooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    textbook: Mapped["Textbook"] = relationship(back_populates="topic_links")
    topic: Mapped["Topic"] = relationship()


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("grade BETWEEN 1 AND 11", name="grade_range"),
        {"schema": "lms"},
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    teacher: Mapped["User"] = relationship()
    school: Mapped["School | None"] = relationship()
    topic_links: Mapped[list["CourseTopic"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    class_links: Mapped[list["CourseClass"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class CourseTopic(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "course_topics"
    __table_args__ = (
        UniqueConstraint("course_id", "topic_id", name="uq_course_topics_course_topic"),
        {"schema": "lms"},
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    course: Mapped["Course"] = relationship(back_populates="topic_links")
    topic: Mapped["Topic"] = relationship()


class CourseClass(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "course_classes"
    __table_args__ = (
        UniqueConstraint("course_id", "class_id", name="uq_course_classes_course_class"),
        {"schema": "lms"},
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    course: Mapped["Course"] = relationship(back_populates="class_links")
    school_class: Mapped["SchoolClass"] = relationship()


class LibraryItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "library_items"
    __table_args__ = {"schema": "lms"}

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    textbook_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.textbooks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    class_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    textbook: Mapped["Textbook | None"] = relationship()
    subject: Mapped["Subject | None"] = relationship()
    class_links: Mapped[list["LibraryItemClass"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class LibraryItemClass(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "library_item_classes"
    __table_args__ = (
        UniqueConstraint("book_id", "class_id", name="uq_library_item_classes_book_class"),
        {"schema": "lms"},
    )

    book_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.library_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped["LibraryItem"] = relationship(back_populates="class_links")
    school_class: Mapped["SchoolClass"] = relationship()


class LibraryRecommendation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "library_recommendations"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('class','student')", name="target_type"
        ),
        {"schema": "lms"},
    )

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.library_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="class", server_default="class"
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    class_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    book: Mapped["LibraryItem"] = relationship()
    topic: Mapped["Topic | None"] = relationship()
    teacher: Mapped["User"] = relationship(foreign_keys=[teacher_id])
    student: Mapped["User | None"] = relationship(foreign_keys=[student_id])


class LibraryRecommendationStatus(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "library_recommendation_status"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            "student_id",
            name="uq_library_recommendation_status_rec_student",
        ),
        {"schema": "lms"},
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.library_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    done_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserBadge(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_key", name="uq_user_badges_user_badge"),
        {"schema": "lms"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
