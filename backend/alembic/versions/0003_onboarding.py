"""Personalised onboarding service.

Revision ID: 0003_onboarding
Revises: 0002_groups_permissions_services
Create Date: 2026-10-30

The training catalogue itself is versioned in code (``onboarding_catalog.py``)
and is personalised at request time from the services and permissions that are
enabled for the learner.  The database stores only the per-user curriculum
state and module progress, which keeps content releases independent from
learner data.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_onboarding"
down_revision: Union[str, None] = "0002_groups_permissions_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "onboarding"')

    op.create_table(
        "profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "known_service_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "catalog_version",
            sa.String(length=32),
            server_default="1.0.0",
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        sa.UniqueConstraint("user_id", name="uq_profiles_user_id"),
        schema="onboarding",
    )
    op.create_index(
        "ix_onboarding_profiles_user_id",
        "profiles",
        ["user_id"],
        unique=True,
        schema="onboarding",
    )

    op.create_table(
        "module_progress",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_code", sa.String(length=128), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column("current_step_code", sa.String(length=128), nullable=True),
        sa.Column(
            "completed_step_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('not_started','in_progress','completed','skipped')",
            name="ck_module_progress_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_module_progress_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_module_progress"),
        sa.UniqueConstraint(
            "user_id",
            "module_code",
            name="uq_module_progress_user_module",
        ),
        schema="onboarding",
    )
    op.create_index(
        "ix_onboarding_module_progress_user",
        "module_progress",
        ["user_id"],
        schema="onboarding",
    )
    op.create_index(
        "ix_onboarding_module_progress_service",
        "module_progress",
        ["service_code"],
        schema="onboarding",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_onboarding_module_progress_service",
        table_name="module_progress",
        schema="onboarding",
    )
    op.drop_index(
        "ix_onboarding_module_progress_user",
        table_name="module_progress",
        schema="onboarding",
    )
    op.drop_table("module_progress", schema="onboarding")
    op.drop_index(
        "ix_onboarding_profiles_user_id",
        table_name="profiles",
        schema="onboarding",
    )
    op.drop_table("profiles", schema="onboarding")
    op.execute('DROP SCHEMA IF EXISTS "onboarding" CASCADE')
