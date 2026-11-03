"""Education levels, academic programmes and professional profiles.

Revision ID: 0004_education_levels
Revises: 0003_onboarding
Create Date: 2026-11-03

The platform now serves primary, secondary, vocational and higher education.
An institution declares the levels it offers; classes carry an education level
and may belong to a programme.  Colleges and universities additionally use
academic programmes, student record-book profiles and staff academic profiles.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_education_levels"
down_revision: Union[str, None] = "0003_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)


def upgrade() -> None:
    op.create_table(
        "education_programs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("qualification", sa.String(length=255), nullable=True),
        sa.Column("duration_years", sa.Integer(), nullable=True),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_education_programs_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_education_programs"),
        sa.UniqueConstraint(
            "institution_id",
            "code",
            name="uq_education_programs_institution_code",
        ),
        schema="org",
    )
    op.create_index(
        "ix_org_education_programs_institution_id",
        "education_programs",
        ["institution_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_education_programs_education_level",
        "education_programs",
        ["education_level"],
        schema="org",
    )

    op.add_column(
        "schools",
        sa.Column(
            "institution_type",
            sa.String(length=32),
            server_default="school",
            nullable=False,
        ),
        schema="org",
    )
    op.add_column(
        "schools",
        sa.Column(
            "education_levels",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("jsonb_build_array('primary', 'secondary')"),
            nullable=False,
        ),
        schema="org",
    )
    op.add_column(
        "schools",
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="org",
    )

    op.add_column(
        "classes",
        sa.Column(
            "education_level",
            sa.String(length=24),
            server_default="secondary",
            nullable=False,
        ),
        schema="org",
    )
    op.add_column(
        "classes",
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="org",
    )
    op.add_column(
        "classes",
        sa.Column("course_year", sa.Integer(), nullable=True),
        schema="org",
    )
    op.add_column(
        "classes",
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="org",
    )
    op.create_foreign_key(
        "fk_classes_program_id_education_programs",
        "classes",
        "education_programs",
        ["program_id"],
        ["id"],
        source_schema="org",
        referent_schema="org",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_org_classes_education_level",
        "classes",
        ["education_level"],
        schema="org",
    )
    op.create_index(
        "ix_org_classes_program_id",
        "classes",
        ["program_id"],
        schema="org",
    )
    op.create_check_constraint(
        "education_level",
        "classes",
        LEVEL_SQL,
        schema="org",
    )

    op.execute(
        """
        UPDATE org.classes
        SET education_level = CASE
            WHEN grade BETWEEN 1 AND 4 THEN 'primary'
            ELSE 'secondary'
        END
        WHERE education_level = 'secondary'
        """
    )

    op.create_table(
        "student_academic_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("course_year", sa.Integer(), nullable=True),
        sa.Column("record_book_number", sa.String(length=64), nullable=True),
        sa.Column(
            "funding_type",
            sa.String(length=16),
            server_default="budget",
            nullable=False,
        ),
        sa.Column("enrollment_year", sa.Integer(), nullable=True),
        sa.Column(
            "academic_status",
            sa.String(length=24),
            server_default="active",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "funding_type IN ('budget','paid','target','other')",
            name="funding_type",
        ),
        sa.CheckConstraint(
            "academic_status IN "
            "('active','academic_leave','expelled','graduated')",
            name="academic_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_student_academic_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_student_academic_profiles_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["org.education_programs.id"],
            name="fk_student_academic_profiles_program_id_education_programs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["org.classes.id"],
            name="fk_student_academic_profiles_group_id_classes",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_student_academic_profiles"),
        sa.UniqueConstraint("user_id", name="uq_student_academic_profiles_user"),
        schema="org",
    )
    op.create_index(
        "ix_org_student_academic_profiles_user_id",
        "student_academic_profiles",
        ["user_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_student_academic_profiles_institution_id",
        "student_academic_profiles",
        ["institution_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_student_academic_profiles_program_id",
        "student_academic_profiles",
        ["program_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_student_academic_profiles_group_id",
        "student_academic_profiles",
        ["group_id"],
        schema="org",
    )

    op.create_table(
        "staff_academic_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("position", sa.String(length=128), nullable=True),
        sa.Column("academic_degree", sa.String(length=128), nullable=True),
        sa.Column("academic_title", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_staff_academic_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_staff_academic_profiles_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_staff_academic_profiles"),
        sa.UniqueConstraint("user_id", name="uq_staff_academic_profiles_user"),
        schema="org",
    )
    op.create_index(
        "ix_org_staff_academic_profiles_user_id",
        "staff_academic_profiles",
        ["user_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_staff_academic_profiles_institution_id",
        "staff_academic_profiles",
        ["institution_id"],
        schema="org",
    )


def downgrade() -> None:
    op.drop_table("staff_academic_profiles", schema="org")
    op.drop_table("student_academic_profiles", schema="org")
    op.drop_constraint(
        "education_level", "classes", schema="org", type_="check"
    )
    op.drop_index("ix_org_classes_program_id", table_name="classes", schema="org")
    op.drop_index(
        "ix_org_classes_education_level", table_name="classes", schema="org"
    )
    op.drop_constraint(
        "fk_classes_program_id_education_programs",
        "classes",
        schema="org",
        type_="foreignkey",
    )
    op.drop_column("classes", "profile", schema="org")
    op.drop_column("classes", "course_year", schema="org")
    op.drop_column("classes", "program_id", schema="org")
    op.drop_column("classes", "education_level", schema="org")
    op.drop_column("schools", "profile", schema="org")
    op.drop_column("schools", "education_levels", schema="org")
    op.drop_column("schools", "institution_type", schema="org")
    op.drop_table("education_programs", schema="org")
