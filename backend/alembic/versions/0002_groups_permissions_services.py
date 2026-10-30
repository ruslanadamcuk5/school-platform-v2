"""Hierarchical groups, permissions and the service catalog.

Revision ID: 0002_groups_permissions_services
Revises: 2c27d5a2ed88
Create Date: 2026-10-30

The migration introduces the group-based access model requested for the
republican platform:

* ``iam.groups``                 hierarchical groups at country/region/city/school/class;
* ``iam.group_memberships``      users belong to groups, not to individual permissions;
* ``iam.permissions``            capability catalog published by services;
* ``iam.group_permissions``      allow/deny grants with inheritance and expiry;
* ``system.services``            microservice catalog;
* ``system.service_activations`` per-scope on/off switches.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_groups_permissions_services"
down_revision: Union[str, None] = "2c27d5a2ed88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCOPE_SQL = "scope_type IN ('country','region','city','school','class')"
CATEGORY_SQL = (
    "category IN ('students','teachers','administration','methodologists',"
    "'psychologists','secretaries','parents','other')"
)
EFFECT_SQL = "effect IN ('allow','deny')"


def upgrade() -> None:
    # ------------------------------------------------------------- iam.groups
    op.create_table(
        "groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.String(length=32),
            server_default="other",
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "meta",
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
        sa.CheckConstraint(SCOPE_SQL, name="scope_type"),
        sa.CheckConstraint(CATEGORY_SQL, name="category"),
        sa.CheckConstraint("depth BETWEEN 0 AND 4", name="depth_range"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["iam.groups.id"],
            name="fk_groups_parent_id_groups",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_groups"),
        sa.UniqueConstraint(
            "scope_type", "scope_id", "code", name="uq_groups_scope_code"
        ),
        schema="iam",
    )
    op.create_index(
        "ix_iam_groups_scope", "groups", ["scope_type", "scope_id"], schema="iam"
    )
    op.create_index("ix_iam_groups_category", "groups", ["category"], schema="iam")
    op.create_index(
        "ix_groups_parent_id", "groups", ["parent_id"], schema="iam"
    )

    # -------------------------------------------------- iam.group_memberships
    op.create_table(
        "group_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["iam.groups.id"],
            name="fk_group_memberships_group_id_groups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_group_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["iam.users.id"],
            name="fk_group_memberships_assigned_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_group_memberships"),
        sa.UniqueConstraint(
            "group_id", "user_id", name="uq_group_memberships_group_user"
        ),
        schema="iam",
    )
    op.create_index(
        "ix_group_memberships_group_id",
        "group_memberships",
        ["group_id"],
        schema="iam",
    )
    op.create_index(
        "ix_group_memberships_user_id",
        "group_memberships",
        ["user_id"],
        schema="iam",
    )

    # -------------------------------------------------------- iam.permissions
    op.create_table(
        "permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service_code", postgresql.CITEXT(), nullable=False),
        sa.Column(
            "category",
            sa.String(length=16),
            server_default="use",
            nullable=False,
        ),
        sa.Column(
            "is_system", sa.Boolean(), server_default=sa.text("true"), nullable=False
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
            "category IN ('read','write','admin','use')",
            name="category",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        schema="iam",
    )
    op.create_index(
        "ix_permissions_code", "permissions", ["code"], unique=True, schema="iam"
    )
    op.create_index(
        "ix_permissions_service_code",
        "permissions",
        ["service_code"],
        schema="iam",
    )

    # --------------------------------------------------- iam.group_permissions
    op.create_table(
        "group_permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "effect", sa.String(length=8), server_default="allow", nullable=False
        ),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(EFFECT_SQL, name="effect"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["iam.groups.id"],
            name="fk_group_permissions_group_id_groups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["iam.permissions.id"],
            name="fk_group_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["iam.users.id"],
            name="fk_group_permissions_granted_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_group_permissions"),
        sa.UniqueConstraint(
            "group_id",
            "permission_id",
            name="uq_group_permissions_group_permission",
        ),
        schema="iam",
    )
    op.create_index(
        "ix_group_permissions_group_id",
        "group_permissions",
        ["group_id"],
        schema="iam",
    )
    op.create_index(
        "ix_group_permissions_permission_id",
        "group_permissions",
        ["permission_id"],
        schema="iam",
    )

    # --------------------------------------------------------- system.services
    op.create_table(
        "services",
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "version", sa.String(length=32), server_default="1.0.0", nullable=False
        ),
        sa.Column(
            "category",
            sa.String(length=32),
            server_default="education",
            nullable=False,
        ),
        sa.Column(
            "api_prefix", sa.String(length=64), server_default="", nullable=False
        ),
        sa.Column("icon", sa.String(length=32), server_default="рџ§©", nullable=False),
        sa.Column(
            "default_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_core", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=16), server_default="active", nullable=False
        ),
        sa.Column(
            "manifest",
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
            "category IN ('core','education','management','communication',"
            "'analytics','ai','security')",
            name="category",
        ),
        sa.CheckConstraint(
            "status IN ('active','beta','disabled')", name="status"
        ),
        sa.PrimaryKeyConstraint("code", name="pk_services"),
        schema="system",
    )

    # ----------------------------------------------- system.service_activations
    op.create_table(
        "service_activations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("service_code", postgresql.CITEXT(), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.CheckConstraint(SCOPE_SQL, name="scope_type"),
        sa.CheckConstraint(
            "depth BETWEEN 0 AND 4", name="depth_range"
        ),
        sa.ForeignKeyConstraint(
            ["service_code"],
            ["system.services.code"],
            name="fk_service_activations_service_code_services",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["iam.users.id"],
            name="fk_service_activations_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_activations"),
        sa.UniqueConstraint(
            "service_code",
            "scope_type",
            "scope_id",
            name="uq_service_activations_service_scope",
        ),
        schema="system",
    )
    op.create_index(
        "ix_service_activations_service_code",
        "service_activations",
        ["service_code"],
        schema="system",
    )
    op.create_index(
        "ix_system_service_activations_scope",
        "service_activations",
        ["scope_type", "scope_id"],
        schema="system",
    )


def downgrade() -> None:
    op.drop_table("service_activations", schema="system")
    op.drop_table("services", schema="system")
    op.drop_table("group_permissions", schema="iam")
    op.drop_table("permissions", schema="iam")
    op.drop_table("group_memberships", schema="iam")
    op.drop_table("groups", schema="iam")
