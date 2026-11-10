"""MFA/TOTP fields and one-time recovery codes.

Revision ID: 0011_mfa
Revises: 0010_safety
Create Date: 2026-11-09
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0011_mfa"
down_revision: Union[str, None] = "0010_safety"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
UUID_SERVER_DEFAULT = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column("mfa_pending_secret_encrypted", sa.Text(), nullable=True),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column("mfa_last_used_counter", sa.BigInteger(), nullable=True),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_failed_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        schema="iam",
    )
    op.add_column(
        "users",
        sa.Column("mfa_locked_until", sa.DateTime(timezone=True), nullable=True),
        schema="iam",
    )
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "mfa_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="iam",
    )

    op.create_table(
        "mfa_recovery_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["iam.users.id"],
            name="fk_mfa_recovery_codes_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="iam",
    )
    op.create_index(
        "ix_iam_mfa_recovery_codes_user_id",
        "mfa_recovery_codes",
        ["user_id"],
        schema="iam",
    )
    op.create_index(
        "ix_iam_mfa_recovery_codes_code_hash",
        "mfa_recovery_codes",
        ["code_hash"],
        unique=True,
        schema="iam",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_iam_mfa_recovery_codes_code_hash",
        table_name="mfa_recovery_codes",
        schema="iam",
    )
    op.drop_index(
        "ix_iam_mfa_recovery_codes_user_id",
        table_name="mfa_recovery_codes",
        schema="iam",
    )
    op.drop_table("mfa_recovery_codes", schema="iam")

    op.drop_column("refresh_tokens", "mfa_verified", schema="iam")
    op.drop_column("users", "mfa_locked_until", schema="iam")
    op.drop_column("users", "mfa_failed_attempts", schema="iam")
    op.drop_column("users", "mfa_last_used_counter", schema="iam")
    op.drop_column("users", "mfa_enrolled_at", schema="iam")
    op.drop_column("users", "mfa_pending_secret_encrypted", schema="iam")
    op.drop_column("users", "mfa_secret_encrypted", schema="iam")
    op.drop_column("users", "mfa_enabled", schema="iam")
