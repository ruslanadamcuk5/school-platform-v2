"""Initial IAM, organisation and audit schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_SQL = (
    "role IN ('superadmin','admin','methodologist','teacher','student',"
    "'parent','psychologist','secretary')"
)


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("director", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_schools"),
        schema="org",
    )
    op.create_index("ix_org_schools_code", "schools", ["code"], unique=True, schema="org")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("login", postgresql.CITEXT(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="student", nullable=False),
        sa.Column("first_name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("last_name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("middle_name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("avatar", sa.String(length=32), server_default="👤", nullable=False),
        sa.Column("locale", sa.String(length=8), server_default="ru", nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Europe/Minsk",
            nullable=False,
        ),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
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
        sa.CheckConstraint(ROLE_SQL, name="ck_users_role"),
        sa.CheckConstraint("version >= 1", name="ck_users_version_positive"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_users_school_id_schools",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        schema="iam",
    )
    op.create_index("ix_iam_users_school_id", "users", ["school_id"], schema="iam")
    op.create_index("ix_iam_users_login", "users", ["login"], unique=True, schema="iam")
    op.create_index("ix_iam_users_email", "users", ["email"], unique=True, schema="iam")
    op.create_index("ix_iam_users_role", "users", ["role"], schema="iam")

    op.create_table(
        "classes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("letter", sa.String(length=8), server_default="А", nullable=False),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("academic_year", sa.String(length=9), nullable=False),
        sa.Column("homeroom_teacher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("grade BETWEEN 1 AND 11", name="ck_classes_grade_range"),
        sa.ForeignKeyConstraint(
            ["homeroom_teacher_id"],
            ["iam.users.id"],
            name="fk_classes_homeroom_teacher_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_classes_school_id_schools",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_classes"),
        sa.UniqueConstraint(
            "school_id",
            "grade",
            "letter",
            "academic_year",
            name="uq_classes_school_grade_letter_year",
        ),
        schema="org",
    )
    op.create_index("ix_org_classes_school_id", "classes", ["school_id"], schema="org")
    op.create_index(
        "ix_org_classes_homeroom_teacher_id",
        "classes",
        ["homeroom_teacher_id"],
        schema="org",
    )

    op.create_table(
        "class_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role_in_class",
            sa.String(length=32),
            server_default="student",
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role_in_class IN ('student','teacher','assistant')",
            name="ck_class_memberships_role_in_class",
        ),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["org.classes.id"],
            name="fk_class_memberships_class_id_classes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_class_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_class_memberships"),
        sa.UniqueConstraint("class_id", "user_id", name="uq_class_memberships_class_user"),
        schema="org",
    )
    op.create_index(
        "ix_org_class_memberships_class_id",
        "class_memberships",
        ["class_id"],
        schema="org",
    )
    op.create_index(
        "ix_org_class_memberships_user_id",
        "class_memberships",
        ["user_id"],
        schema="org",
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        schema="iam",
    )
    op.create_index(
        "ix_iam_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="iam"
    )
    op.create_index(
        "ix_iam_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="iam",
    )
    op.create_index(
        "ix_iam_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
        schema="iam",
    )

    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_events_school_id_schools",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_events_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
        schema="audit",
    )
    op.create_index("ix_audit_events_school_id", "events", ["school_id"], schema="audit")
    op.create_index("ix_audit_events_user_id", "events", ["user_id"], schema="audit")
    op.create_index("ix_audit_events_action", "events", ["action"], schema="audit")
    op.create_index(
        "ix_audit_events_entity_type", "events", ["entity_type"], schema="audit"
    )
    op.create_index("ix_audit_events_created_at", "events", ["created_at"], schema="audit")


def downgrade() -> None:
    op.drop_table("events", schema="audit")
    op.drop_table("refresh_tokens", schema="iam")
    op.drop_table("class_memberships", schema="org")
    op.drop_table("classes", schema="org")
    op.drop_table("users", schema="iam")
    op.drop_table("schools", schema="org")
