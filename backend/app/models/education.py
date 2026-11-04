"""Academic programs and profiles for vocational and higher education.

Schools use the existing ``org.classes`` and ``org.class_memberships`` model.
Colleges and universities need richer academic data, so this module adds
reusable programmes, student record-book profiles and staff profiles without
breaking the school workflow.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
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
SESSION_STATUS_SQL = "status IN ('planned','active','completed','archived')"
SESSION_TYPE_SQL = "session_type IN ('winter','summer','additional','other')"
STATEMENT_STATUS_SQL = "status IN ('draft','published','approved','archived')"
STATEMENT_RESULT_SQL = (
    "result IN ('planned','passed','failed','not_appeared','exempt','transferred')"
)
TRANSFER_STATUS_SQL = (
    "status IN ('draft','pending','approved','rejected','archived')"
)
COMPETENCY_TYPE_SQL = (
    "competency_type IN ('universal','general','professional','other')"
)
PRACTICE_CONTRACT_STATUS_SQL = (
    "status IN ('draft','signed','active','completed','terminated','archived')"
)
PRACTICE_PLACEMENT_STATUS_SQL = (
    "status IN ('planned','active','completed','failed','cancelled','archived')"
)
PRACTICE_RESULT_SQL = (
    "result IN ('not_assessed','passed','failed','exempt')"
)
DIARY_STATUS_SQL = "status IN ('draft','submitted','approved','rejected')"


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
    competency_links: Mapped[list["ProgramCompetency"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramCompetency.competency_id",
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
    competency_links: Mapped[list["ComponentCompetency"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
        order_by="ComponentCompetency.competency_id",
    )


class AcademicSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Examination session for a professional institution."""

    __tablename__ = "academic_sessions"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "academic_year",
            "semester",
            "name",
            name="uq_academic_sessions_institution_year_semester_name",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(SESSION_STATUS_SQL, name="status"),
        CheckConstraint(SESSION_TYPE_SQL, name="session_type"),
        CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        CheckConstraint("semester BETWEEN 1 AND 12", name="semester_range"),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(
        String(9), nullable=False, index=True
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    session_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="winter", server_default="winter"
    )
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="planned", server_default="planned"
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    institution: Mapped["School"] = relationship()
    statements: Mapped[list["SessionStatement"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionStatement.statement_number",
    )


class SessionStatement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Examination statement for one group and one curriculum component."""

    __tablename__ = "session_statements"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "group_id",
            "component_id",
            name="uq_session_statements_session_group_component",
        ),
        UniqueConstraint(
            "institution_id",
            "statement_number",
            name="uq_session_statements_institution_number",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(STATEMENT_STATUS_SQL, name="status"),
        {"schema": "org"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_curricula.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.curriculum_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    statement_number: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_on: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("CURRENT_DATE")
    )
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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    session: Mapped["AcademicSession"] = relationship(back_populates="statements")
    institution: Mapped["School"] = relationship()
    group: Mapped["SchoolClass"] = relationship()
    curriculum: Mapped["EducationCurriculum"] = relationship()
    component: Mapped["CurriculumComponent"] = relationship()
    teacher: Mapped["User | None"] = relationship(foreign_keys=[teacher_id])
    approved_by: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by_id]
    )
    records: Mapped[list["StatementRecord"]] = relationship(
        back_populates="statement",
        cascade="all, delete-orphan",
        order_by="StatementRecord.student_id",
    )


class StatementRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Result of one student in an examination statement."""

    __tablename__ = "statement_records"
    __table_args__ = (
        UniqueConstraint(
            "statement_id",
            "student_id",
            name="uq_statement_records_statement_student",
        ),
        CheckConstraint(STATEMENT_RESULT_SQL, name="result"),
        CheckConstraint(
            "grade IS NULL OR (grade BETWEEN 1 AND 10)", name="grade_range"
        ),
        CheckConstraint(
            "credits_awarded >= 0 AND credits_awarded <= 100",
            name="credits_range",
        ),
        {"schema": "org"},
    )

    statement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.session_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(
        String(24), nullable=False, default="planned", server_default="planned"
    )
    credits_awarded: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    statement: Mapped["SessionStatement"] = relationship(back_populates="records")
    student: Mapped["User"] = relationship(foreign_keys=[student_id])


class CreditTransfer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Recognition of credits earned at another institution or programme."""

    __tablename__ = "credit_transfers"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "student_id",
            "source_institution",
            "source_component_code",
            "source_academic_year",
            name="uq_credit_transfers_source",
        ),
        CheckConstraint(TRANSFER_STATUS_SQL, name="status"),
        CheckConstraint(
            "source_academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="source_academic_year_format",
        ),
        CheckConstraint(
            "source_credits >= 0 AND source_credits <= 100",
            name="source_credits_range",
        ),
        CheckConstraint(
            "awarded_credits >= 0 AND awarded_credits <= 100",
            name="awarded_credits_range",
        ),
        CheckConstraint(
            "source_grade IS NULL OR (source_grade BETWEEN 1 AND 10)",
            name="source_grade_range",
        ),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_program_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_component_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.curriculum_components.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_institution: Mapped[str] = mapped_column(String(255), nullable=False)
    source_program: Mapped[str] = mapped_column(String(255), nullable=False)
    source_component_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    source_credits: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    awarded_credits: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    source_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
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

    institution: Mapped["School"] = relationship()
    student: Mapped["User"] = relationship(foreign_keys=[student_id])
    target_program: Mapped["EducationProgram | None"] = relationship()
    target_component: Mapped["CurriculumComponent | None"] = relationship()
    decided_by: Mapped["User | None"] = relationship(
        foreign_keys=[decided_by_id]
    )


class Competency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A universal, general or professional competency."""

    __tablename__ = "competencies"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "code",
            name="uq_competencies_institution_code",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(COMPETENCY_TYPE_SQL, name="competency_type"),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    competency_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="professional",
        server_default="professional",
        index=True,
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    institution: Mapped["School"] = relationship()
    program_links: Mapped[list["ProgramCompetency"]] = relationship(
        back_populates="competency",
        cascade="all, delete-orphan",
    )
    component_links: Mapped[list["ComponentCompetency"]] = relationship(
        back_populates="competency",
        cascade="all, delete-orphan",
    )


class ProgramCompetency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Target level of a competency in an education programme."""

    __tablename__ = "program_competencies"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "competency_id",
            name="uq_program_competencies_program_competency",
        ),
        CheckConstraint(
            "target_level IS NULL OR (target_level BETWEEN 1 AND 5)",
            name="target_level_range",
        ),
        CheckConstraint(
            "weight >= 0 AND weight <= 100", name="weight_range"
        ),
        {"schema": "org"},
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.competencies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    program: Mapped["EducationProgram"] = relationship(
        back_populates="competency_links"
    )
    competency: Mapped["Competency"] = relationship(
        back_populates="program_links"
    )


class ComponentCompetency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Contribution of a curriculum component to a competency."""

    __tablename__ = "component_competencies"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "competency_id",
            name="uq_component_competencies_component_competency",
        ),
        CheckConstraint(
            "weight >= 0 AND weight <= 100", name="weight_range"
        ),
        {"schema": "org"},
    )

    component_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.curriculum_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.competencies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weight: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    component: Mapped["CurriculumComponent"] = relationship(
        back_populates="competency_links"
    )
    competency: Mapped["Competency"] = relationship(
        back_populates="component_links"
    )


class PracticePlace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Enterprise or organisation that accepts students for practice."""

    __tablename__ = "practice_places"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "code",
            name="uq_practice_places_institution_code",
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
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    institution: Mapped["School"] = relationship()
    contracts: Mapped[list["PracticeContract"]] = relationship(
        back_populates="place", cascade="all, delete-orphan"
    )


class PracticeContract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Agreement between an institution and an enterprise."""

    __tablename__ = "practice_contracts"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "contract_number",
            name="uq_practice_contracts_institution_number",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(PRACTICE_CONTRACT_STATUS_SQL, name="status"),
        CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        CheckConstraint("ends_on >= starts_on", name="date_range"),
        {"schema": "org"},
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    practice_place_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.practice_places.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.education_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.curriculum_components.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract_number: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_year: Mapped[str] = mapped_column(
        String(9), nullable=False, index=True
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    signed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    responsible_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    institution: Mapped["School"] = relationship()
    place: Mapped["PracticePlace"] = relationship(back_populates="contracts")
    program: Mapped["EducationProgram | None"] = relationship()
    component: Mapped["CurriculumComponent | None"] = relationship()
    responsible: Mapped["User | None"] = relationship(
        foreign_keys=[responsible_id]
    )
    placements: Mapped[list["PracticePlacement"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )


class PracticePlacement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Assignment of one student to a practice under a contract."""

    __tablename__ = "practice_placements"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "student_id",
            name="uq_practice_placements_contract_student",
        ),
        CheckConstraint(LEVEL_SQL, name="education_level"),
        CheckConstraint(PRACTICE_PLACEMENT_STATUS_SQL, name="status"),
        CheckConstraint(PRACTICE_RESULT_SQL, name="result"),
        CheckConstraint("ends_on >= starts_on", name="date_range"),
        CheckConstraint(
            "total_hours >= 0 AND total_hours <= 2000",
            name="total_hours_range",
        ),
        CheckConstraint(
            "grade IS NULL OR (grade BETWEEN 1 AND 10)", name="grade_range"
        ),
        {"schema": "org"},
    )

    contract_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.practice_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    education_level: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.classes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.curriculum_components.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    enterprise_supervisor: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    total_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="planned", server_default="planned"
    )
    result: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="not_assessed",
        server_default="not_assessed",
    )
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assessed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    contract: Mapped["PracticeContract"] = relationship(
        back_populates="placements"
    )
    institution: Mapped["School"] = relationship()
    student: Mapped["User"] = relationship(foreign_keys=[student_id])
    group: Mapped["SchoolClass | None"] = relationship()
    component: Mapped["CurriculumComponent | None"] = relationship()
    supervisor: Mapped["User | None"] = relationship(
        foreign_keys=[supervisor_id]
    )
    assessed_by: Mapped["User | None"] = relationship(
        foreign_keys=[assessed_by_id]
    )
    diary_entries: Mapped[list["PracticeDiaryEntry"]] = relationship(
        back_populates="placement",
        cascade="all, delete-orphan",
        order_by="PracticeDiaryEntry.entry_date",
    )


class PracticeDiaryEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily practice record written by a student or their supervisor."""

    __tablename__ = "practice_diary_entries"
    __table_args__ = (
        CheckConstraint(DIARY_STATUS_SQL, name="status"),
        CheckConstraint(
            "hours >= 0 AND hours <= 24", name="hours_range"
        ),
        {"schema": "org"},
    )

    placement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.practice_placements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hours: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    activity: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    supervisor_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    placement: Mapped["PracticePlacement"] = relationship(
        back_populates="diary_entries"
    )
    approved_by: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by_id]
    )
