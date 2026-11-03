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
    Numeric,
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
CURRICULUM_STATUS_SQL = "status IN ('draft','approved','archived')"
COMPONENT_TYPE_SQL = (
    "component_type IN "
    "('discipline','module','practice','coursework','internship','other')"
)
ASSESSMENT_TYPE_SQL = (
    "assessment_type IN "
    "('exam','credit','differentiated_credit','coursework','practice_report','other')"
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
    curricula: Mapped[list["EducationCurriculum"]] = relationship(
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


class EducationCurriculum(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Curriculum (учебный план) for a professional education programme."""

    __tablename__ = "education_curricula"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "academic_year",
            "name",
            name="uq_education_curricula_program_year_name",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(CURRICULUM_STATUS_SQL, name="status"),
        CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(
        String(9), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    institution: Mapped["School"] = relationship(back_populates="curricula")
    program: Mapped["EducationProgram"] = relationship(back_populates="curricula")
    approved_by: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by_id]
    )
    components: Mapped[list["CurriculumComponent"]] = relationship(
        back_populates="curriculum",
        cascade="all, delete-orphan",
        order_by="CurriculumComponent.order_index",
    )


class CurriculumComponent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A discipline, module, practice or coursework inside a curriculum."""

    __tablename__ = "curriculum_components"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_id",
            "code",
            name="uq_curriculum_components_curriculum_code",
        ),
        CheckConstraint(COMPONENT_TYPE_SQL, name="component_type"),
        CheckConstraint(ASSESSMENT_TYPE_SQL, name="assessment_type"),
        CheckConstraint("semester BETWEEN 1 AND 12", name="semester_range"),
        CheckConstraint(
            "credits >= 0 AND credits <= 100", name="credits_range"
        ),
        CheckConstraint(
            "academic_hours >= 0 AND academic_hours <= 20000",
            name="academic_hours_range",
        ),
        CheckConstraint(
            "contact_hours >= 0 AND contact_hours <= academic_hours",
            name="contact_hours_range",
        ),
        CheckConstraint("order_index >= 0", name="order_index_non_negative"),
        {"schema": "org"},
    )

    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_curricula.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="discipline", server_default="discipline"
    )
    semester: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    credits: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    academic_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    contact_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    assessment_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="exam", server_default="exam"
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    curriculum: Mapped["EducationCurriculum"] = relationship(
        back_populates="components"
    )
