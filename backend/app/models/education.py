"""Academic programs and profiles for vocational and higher education.

Schools use the existing ``org.classes`` and ``org.class_memberships`` model.
Colleges and universities need richer academic data, so this module adds
reusable programmes, student record-book profiles and staff profiles without
breaking the school workflow.
"""
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.iam import User
    from app.models.org import School, SchoolClass


LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)
FUNDING_SQL = "funding_type IN ('budget','paid','target','other')"
STATUS_SQL = (
    "academic_status IN ('active','academic_leave','expelled','graduated')"
)


class EducationProgram(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A specialty / educational programme offered by an institution."""

    __tablename__ = "education_programs"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "code",
            name="uq_education_programs_institution_code",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    institution: Mapped["School"] = relationship(back_populates="programs")
    groups: Mapped[list["SchoolClass"]] = relationship(back_populates="program")
    student_profiles: Mapped[list["StudentAcademicProfile"]] = relationship(
        back_populates="program"
    )


class StudentAcademicProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Academic record for a student in a professional institution."""

    __tablename__ = "student_academic_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_student_academic_profiles_user"),
        CheckConstraint(FUNDING_SQL, name="funding_type"),
        CheckConstraint(STATUS_SQL, name="academic_status"),
        {"schema": "org"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_book_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    funding_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="budget", server_default="budget"
    )
    enrollment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    academic_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="active", server_default="active"
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    institution: Mapped["School"] = relationship(
        back_populates="student_profiles"
    )
    program: Mapped["EducationProgram | None"] = relationship(
        back_populates="student_profiles"
    )
    group: Mapped["SchoolClass | None"] = relationship()


class StaffAcademicProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Academic profile of a teacher or researcher in a professional institution."""

    __tablename__ = "staff_academic_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_staff_academic_profiles_user"),
        {"schema": "org"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(128), nullable=True)
    academic_degree: Mapped[str | None] = mapped_column(String(128), nullable=True)
    academic_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    institution: Mapped["School"] = relationship()
