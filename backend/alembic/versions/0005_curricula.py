"""Curricula, credits and practice components for professional education.

Revision ID: 0005_curricula
Revises: 0004_education_levels
Create Date: 2026-11-03

A programme gets one or more curricula per academic year.  Each curriculum
contains disciplines, modules, coursework, practice and internships with
credits, hours, semester and assessment type.  This is the foundation for
grade books and credit transfer in the next stages.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_curricula"
down_revision: Union[str, None] = "0004_education_levels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)


def upgrade() -> None:
    op.create_table(
        "education_curricula",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("academic_year", sa.String(length=9), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(LEVEL_SQL, name="education_level"),
        sa.CheckConstraint(
            "status IN ('draft','approved','archived')",
            name="status",
        ),
        sa.CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_education_curricula_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["org.education_programs.id"],
            name="fk_education_curricula_program_id_education_programs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["iam.users.id"],
            name="fk_education_curricula_approved_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_education_curricula"),
        sa.UniqueConstraint(
            "program_id",
            "academic_year",
            "name",
            name="uq_education_curricula_program_year_name",
        ),
        schema="org",
    )
    op.create_index(
        "ix_org_education_curricula_institution_id",
        "education_curricula",
        ["institution_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_education_curricula_program_id",
        "education_curricula",
        ["program_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_education_curricula_education_level",
        "education_curricula",
        ["education_level"],
        schema="org",
    )
    op.create_index(
        "ix_org_education_curricula_academic_year",
        "education_curricula",
        ["academic_year"],
        schema="org",
    )

    op.create_table(
        "curriculum_components",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "component_type",
            sa.String(length=24),
            server_default="discipline",
            nullable=False,
        ),
        sa.Column(
            "semester", sa.Integer(), server_default="1", nullable=False
        ),
        sa.Column(
            "credits", sa.Numeric(5, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "academic_hours", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "contact_hours", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "assessment_type",
            sa.String(length=32),
            server_default="exam",
            nullable=False,
        ),
        sa.Column(
            "is_optional", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "component_type IN "
            "('discipline','module','practice','coursework','internship','other')",
            name="component_type",
        ),
        sa.CheckConstraint(
            "assessment_type IN "
            "('exam','credit','differentiated_credit','coursework',"
            "'practice_report','other')",
            name="assessment_type",
        ),
        sa.CheckConstraint("semester BETWEEN 1 AND 12", name="semester_range"),
        sa.CheckConstraint(
            "credits >= 0 AND credits <= 100", name="credits_range"
        ),
        sa.CheckConstraint(
            "academic_hours >= 0 AND academic_hours <= 20000",
            name="academic_hours_range",
        ),
        sa.CheckConstraint(
            "contact_hours >= 0 AND contact_hours <= academic_hours",
            name="contact_hours_range",
        ),
        sa.CheckConstraint("order_index >= 0", name="order_index_non_negative"),
        sa.ForeignKeyConstraint(
            ["curriculum_id"],
            ["org.education_curricula.id"],
            name="fk_curriculum_components_curriculum_id_curricula",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_curriculum_components"),
        sa.UniqueConstraint(
            "curriculum_id",
            "code",
            name="uq_curriculum_components_curriculum_code",
        ),
        schema="org",
    )
    op.create_index(
        "ix_org_curriculum_components_curriculum_id",
        "curriculum_components",
        ["curriculum_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_curriculum_components_component_type",
        "curriculum_components",
        ["component_type"],
        schema="org",
    )
    op.create_index(
        "ix_org_curriculum_components_semester",
        "curriculum_components",
        ["semester"],
        schema="org",
    )


def downgrade() -> None:
    op.drop_table("curriculum_components", schema="org")
    op.drop_table("education_curricula", schema="org")
