"""Practice places, enterprise contracts, placements and diaries.

Revision ID: 0008_practice_contracts
Revises: 0007_competencies
Create Date: 2026-11-04

Professional programmes include practice components.  This migration adds the
missing operational layer: partner enterprises, contracts with them, student
placements, daily diary records and practice assessment.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_practice_contracts"
down_revision: Union[str, None] = "0007_competencies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)
TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
JSON_SERVER_DEFAULT = sa.text("'{}'::jsonb")
UUID_SERVER_DEFAULT = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "practice_places",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=64), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_practice_places_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_practice_places"),
        sa.UniqueConstraint(
            "institution_id",
            "code",
            name="uq_practice_places_institution_code",
        ),
        schema="org",
    )
    for column in ("institution_id", "education_level"):
        op.create_index(
            f"ix_org_practice_places_{column}",
            "practice_places",
            [column],
            schema="org",
        )

    op.create_table(
        "practice_contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column(
            "practice_place_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_number", sa.String(length=64), nullable=False),
        sa.Column("academic_year", sa.String(length=9), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("signed_on", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("responsible_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_number", sa.String(length=64), nullable=True),
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
            "status IN "
            "('draft','signed','active','completed','terminated','archived')",
            name="status",
        ),
        sa.CheckConstraint(
            "academic_year ~ '^[0-9]{4}/[0-9]{4}$'",
            name="academic_year_format",
        ),
        sa.CheckConstraint("ends_on >= starts_on", name="date_range"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_practice_contracts_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["practice_place_id"],
            ["org.practice_places.id"],
            name="fk_practice_contracts_practice_place_id_places",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["org.education_programs.id"],
            name="fk_practice_contracts_program_id_programs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["org.curriculum_components.id"],
            name="fk_practice_contracts_component_id_components",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["responsible_id"],
            ["iam.users.id"],
            name="fk_practice_contracts_responsible_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_practice_contracts"),
        sa.UniqueConstraint(
            "institution_id",
            "contract_number",
            name="uq_practice_contracts_institution_number",
        ),
        schema="org",
    )
    for column in (
        "institution_id",
        "education_level",
        "practice_place_id",
        "program_id",
        "component_id",
        "academic_year",
        "responsible_id",
    ):
        op.create_index(
            f"ix_org_practice_contracts_{column}",
            "practice_contracts",
            [column],
            schema="org",
        )

    op.create_table(
        "practice_placements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "enterprise_supervisor", sa.String(length=255), nullable=True
        ),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column(
            "total_hours", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="planned",
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.String(length=16),
            server_default="not_assessed",
            nullable=False,
        ),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column(
            "assessed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("assessed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "status IN "
            "('planned','active','completed','failed','cancelled','archived')",
            name="status",
        ),
        sa.CheckConstraint(
            "result IN ('not_assessed','passed','failed','exempt')",
            name="result",
        ),
        sa.CheckConstraint("ends_on >= starts_on", name="date_range"),
        sa.CheckConstraint(
            "total_hours >= 0 AND total_hours <= 2000",
            name="total_hours_range",
        ),
        sa.CheckConstraint(
            "grade IS NULL OR (grade BETWEEN 1 AND 10)", name="grade_range"
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["org.practice_contracts.id"],
            name="fk_practice_placements_contract_id_contracts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_practice_placements_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_practice_placements_student_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["org.classes.id"],
            name="fk_practice_placements_group_id_classes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["org.curriculum_components.id"],
            name="fk_practice_placements_component_id_components",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_id"],
            ["iam.users.id"],
            name="fk_practice_placements_supervisor_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assessed_by_id"],
            ["iam.users.id"],
            name="fk_practice_placements_assessed_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_practice_placements"),
        sa.UniqueConstraint(
            "contract_id",
            "student_id",
            name="uq_practice_placements_contract_student",
        ),
        schema="org",
    )
    for column in (
        "contract_id",
        "institution_id",
        "education_level",
        "student_id",
        "group_id",
        "component_id",
        "supervisor_id",
    ):
        op.create_index(
            f"ix_org_practice_placements_{column}",
            "practice_placements",
            [column],
            schema="org",
        )

    op.create_table(
        "practice_diary_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("placement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column(
            "hours",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("supervisor_comment", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "status IN ('draft','submitted','approved','rejected')",
            name="status",
        ),
        sa.CheckConstraint(
            "hours >= 0 AND hours <= 24", name="hours_range"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"],
            ["org.practice_placements.id"],
            name="fk_practice_diary_entries_placement_id_placements",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["iam.users.id"],
            name="fk_practice_diary_entries_approved_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_practice_diary_entries"),
        schema="org",
    )
    for column in ("placement_id", "entry_date"):
        op.create_index(
            f"ix_org_practice_diary_entries_{column}",
            "practice_diary_entries",
            [column],
            schema="org",
        )


def downgrade() -> None:
    op.drop_table("practice_diary_entries", schema="org")
    op.drop_table("practice_placements", schema="org")
    op.drop_table("practice_contracts", schema="org")
    op.drop_table("practice_places", schema="org")
