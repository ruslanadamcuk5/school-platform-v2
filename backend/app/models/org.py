"""Organisation models: schools, classes and class membership."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.iam import User
    from app.models.lms import Subject


class Region(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "regions"
    __table_args__ = {"schema": "org"}

    code: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    cities: Mapped[list["City"]] = relationship(
        back_populates="region", cascade="all, delete-orphan"
    )


class City(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "cities"
    __table_args__ = {"schema": "org"}

    region_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.regions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="city", server_default="city"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    region: Mapped["Region"] = relationship(back_populates="cities")
    schools: Mapped[list["School"]] = relationship(back_populates="city_ref")


class School(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "schools"
    __table_args__ = {"schema": "org"}

    code: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    city_ref: Mapped["City | None"] = relationship(back_populates="schools")
    users: Mapped[list["User"]] = relationship(
        back_populates="school", foreign_keys="User.school_id"
    )
    classes: Mapped[list["SchoolClass"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class SchoolClass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "grade",
            "letter",
            "academic_year",
            name="uq_classes_school_grade_letter_year",
        ),
        CheckConstraint("grade BETWEEN 1 AND 11", name="grade_range"),
        {"schema": "org"},
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    letter: Mapped[str] = mapped_column(
        String(8), nullable=False, default="А", server_default="А"
    )
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    homeroom_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    school: Mapped["School"] = relationship(back_populates="classes")
    homeroom_teacher: Mapped["User | None"] = relationship(
        foreign_keys=[homeroom_teacher_id]
    )
    memberships: Mapped[list["ClassMembership"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        return self.title or f"{self.grade}{self.letter}"


class ClassMembership(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "class_memberships"
    __table_args__ = (
        UniqueConstraint(
            "class_id", "user_id", name="uq_class_memberships_class_user"
        ),
        CheckConstraint(
            "role_in_class IN ('student','teacher','assistant')",
            name="role_in_class",
        ),
        {"schema": "org"},
    )

    class_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_in_class: Mapped[str] = mapped_column(
        String(32), nullable=False, default="student", server_default="student"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    school_class: Mapped["SchoolClass"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()


class TeacherSubject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Teacher workload and subject assignment."""

    __tablename__ = "teacher_subjects"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "subject_id",
            "school_id",
            "class_id",
            name="uq_teacher_subjects_scope",
        ),
        {"schema": "org"},
    )

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workload_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    teacher: Mapped["User"] = relationship(foreign_keys=[teacher_id])
    subject: Mapped["Subject"] = relationship()
    school: Mapped["School"] = relationship()
    school_class: Mapped["SchoolClass | None"] = relationship()
