"""Examination sessions, statements and credit transfer.

Revision ID: 0006_sessions_credits
Revises: 0005_curricula
Create Date: 2026-11-04

Professional institutions need examination sessions and statements before a
student transcript can be issued.  Credit transfer records recognition of
credits earned at another institution or programme and feeds the same
transcript without changing the curriculum itself.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_sessions_credits"
down_revision: Union[str, None] = "0005_curricula"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)
TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
JSON_SERVER_DEFAULT = sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.create_table(
        "academic_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("academic_year", sa.String(length=9), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "session_type",
            sa.String(length=24),
            server_default="winter",
            nullable=False,
        ),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default="planned", nullable=False
        ),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSON_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(LEVEL_SQL, name="education_level"),
        sa.CheckConstraint(
            "status IN ('planned','active','completed','archived')",
            name="status",
        ),
        sa.CheckConstraint(
            "session_type IN ('winter','summer','additional','other')",
            name="session_type",
        ),
        sa.CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        sa.CheckConstraint("semester BETWEEN 1 AND 12", name="semester_range"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_academic_sessions_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academic_sessions"),
        sa.UniqueConstraint(
            "institution_id",
            "academic_year",
            "semester",
            "name",
            name="uq_academic_sessions_institution_year_semester_name",
        ),
        schema="org",
    )
    op.create_index(
        "ix_org_academic_sessions_institution_id",
        "academic_sessions",
        ["institution_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_academic_sessions_education_level",
        "academic_sessions",
        ["education_level"],
        schema="org",
    )
    op.create_index(
        "ix_org_academic_sessions_academic_year",
        "academic_sessions",
        ["academic_year"],
        schema="org",
    )

    op.create_table(
        "session_statements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement_number", sa.String(length=64), nullable=False),
        sa.Column(
            "issued_on",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=16), server_default="draft", nullable=False
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSON_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(LEVEL_SQL, name="education_level"),
        sa.CheckConstraint(
            "status IN ('draft','published','approved','archived')",
            name="status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["org.academic_sessions.id"],
            name="fk_session_statements_session_id_academic_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_session_statements_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["org.classes.id"],
            name="fk_session_statements_group_id_classes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_id"],
            ["org.education_curricula.id"],
            name="fk_session_statements_curriculum_id_curricula",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["org.curriculum_components.id"],
            name="fk_session_statements_component_id_components",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["iam.users.id"],
            name="fk_session_statements_teacher_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["iam.users.id"],
            name="fk_session_statements_approved_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_session_statements"),
        sa.UniqueConstraint(
            "session_id",
            "group_id",
            "component_id",
            name="uq_session_statements_session_group_component",
        ),
        sa.UniqueConstraint(
            "institution_id",
            "statement_number",
            name="uq_session_statements_institution_number",
        ),
        schema="org",
    )
    for column in (
        "session_id",
        "institution_id",
        "education_level",
        "group_id",
        "curriculum_id",
        "component_id",
        "teacher_id",
    ):
        op.create_index(
            f"ix_org_session_statements_{column}",
            "session_statements",
            [column],
            schema="org",
        )

    op.create_table(
        "statement_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column(
            "result",
            sa.String(length=24),
            server_default="planned",
            nullable=False,
        ),
        sa.Column(
            "credits_awarded",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSON_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(
            "result IN "
            "('planned','passed','failed','not_appeared','exempt','transferred')",
            name="result",
        ),
        sa.CheckConstraint(
            "grade IS NULL OR (grade BETWEEN 1 AND 10)", name="grade_range"
        ),
        sa.CheckConstraint(
            "credits_awarded >= 0 AND credits_awarded <= 100",
            name="credits_range",
        ),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["org.session_statements.id"],
            name="fk_statement_records_statement_id_statements",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_statement_records_student_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_statement_records"),
        sa.UniqueConstraint(
            "statement_id",
            "student_id",
            name="uq_statement_records_statement_student",
        ),
        schema="org",
    )
    op.create_index(
        "ix_org_statement_records_statement_id",
        "statement_records",
        ["statement_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_statement_records_student_id",
        "statement_records",
        ["student_id"],
        schema="org",
    )

    op.create_table(
        "credit_transfers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_component_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_institution", sa.String(length=255), nullable=False),
        sa.Column("source_program", sa.String(length=255), nullable=False),
        sa.Column("source_component_code", sa.String(length=64), nullable=False),
        sa.Column("source_component_name", sa.String(length=255), nullable=False),
        sa.Column("source_academic_year", sa.String(length=9), nullable=False),
        sa.Column(
            "source_credits",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "awarded_credits",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("source_grade", sa.Integer(), nullable=True),
        sa.Column("document_number", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default="draft", nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSON_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(LEVEL_SQL, name="education_level"),
        sa.CheckConstraint(
            "status IN ('draft','pending','approved','rejected','archived')",
            name="status",
        ),
        sa.CheckConstraint(
            "source_academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="source_academic_year_format",
        ),
        sa.CheckConstraint(
            "source_credits >= 0 AND source_credits <= 100",
            name="source_credits_range",
        ),
        sa.CheckConstraint(
            "awarded_credits >= 0 AND awarded_credits <= 100",
            name="awarded_credits_range",
        ),
        sa.CheckConstraint(
            "source_grade IS NULL OR (source_grade BETWEEN 1 AND 10)",
            name="source_grade_range",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_credit_transfers_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_credit_transfers_student_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_program_id"],
            ["org.education_programs.id"],
            name="fk_credit_transfers_target_program_id_programs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_component_id"],
            ["org.curriculum_components.id"],
            name="fk_credit_transfers_target_component_id_components",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_id"],
            ["iam.users.id"],
            name="fk_credit_transfers_decided_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_credit_transfers"),
        sa.UniqueConstraint(
            "institution_id",
            "student_id",
            "source_institution",
            "source_component_code",
            "source_academic_year",
            name="uq_credit_transfers_source",
        ),
        schema="org",
    )
    for column in (
        "institution_id",
        "education_level",
        "student_id",
        "target_program_id",
        "target_component_id",
    ):
        op.create_index(
            f"ix_org_credit_transfers_{column}",
            "credit_transfers",
            [column],
            schema="org",
        )


def downgrade() -> None:
    op.drop_table("credit_transfers", schema="org")
    op.drop_table("statement_records", schema="org")
    op.drop_table("session_statements", schema="org")
    op.drop_table("academic_sessions", schema="org")
