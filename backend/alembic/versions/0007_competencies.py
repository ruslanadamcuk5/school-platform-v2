"""Competency catalogue, programme targets and curriculum matrix.

Revision ID: 0007_competencies
Revises: 0006_sessions_credits
Create Date: 2026-11-04

Professional programmes describe what a graduate must be able to do.  The
catalogue stores universal, general and professional competencies.  Programme
links define the target level, while curriculum links show which components
contribute to each competency.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_competencies"
down_revision: Union[str, None] = "0006_sessions_credits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEVEL_SQL = (
    "education_level IN ('primary','secondary','vocational','higher')"
)
TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
JSON_SERVER_DEFAULT = sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.create_table(
        "competencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("education_level", sa.String(length=24), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "competency_type",
            sa.String(length=32),
            server_default="professional",
            nullable=False,
        ),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSON_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
            "competency_type IN ('universal','general','professional','other')",
            name="competency_type",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["org.schools.id"],
            name="fk_competencies_institution_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_competencies"),
        sa.UniqueConstraint(
            "institution_id",
            "code",
            name="uq_competencies_institution_code",
        ),
        schema="org",
    )
    for column in ("institution_id", "education_level", "competency_type"):
        op.create_index(
            f"ix_org_competencies_{column}",
            "competencies",
            [column],
            schema="org",
        )

    op.create_table(
        "program_competencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=True),
        sa.Column(
            "weight",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
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
        sa.CheckConstraint(
            "target_level IS NULL OR (target_level BETWEEN 1 AND 5)",
            name="target_level_range",
        ),
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 100", name="weight_range"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["org.education_programs.id"],
            name="fk_program_competencies_program_id_programs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["org.competencies.id"],
            name="fk_program_competencies_competency_id_competencies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_program_competencies"),
        sa.UniqueConstraint(
            "program_id",
            "competency_id",
            name="uq_program_competencies_program_competency",
        ),
        schema="org",
    )
    for column in ("program_id", "competency_id"):
        op.create_index(
            f"ix_org_program_competencies_{column}",
            "program_competencies",
            [column],
            schema="org",
        )

    op.create_table(
        "component_competencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
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
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 100", name="weight_range"
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["org.curriculum_components.id"],
            name="fk_component_competencies_component_id_components",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["org.competencies.id"],
            name="fk_component_competencies_competency_id_competencies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_component_competencies"),
        sa.UniqueConstraint(
            "component_id",
            "competency_id",
            name="uq_component_competencies_component_competency",
        ),
        schema="org",
    )
    for column in ("component_id", "competency_id"):
        op.create_index(
            f"ix_org_component_competencies_{column}",
            "component_competencies",
            [column],
            schema="org",
        )


def downgrade() -> None:
    op.drop_table("component_competencies", schema="org")
    op.drop_table("program_competencies", schema="org")
    op.drop_table("competencies", schema="org")
