"""Document requests for the secretariat service.

Revision ID: 0009_document_requests
Revises: 0008_practice_contracts
Create Date: 2026-11-04
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_document_requests"
down_revision: Union[str, None] = "0008_practice_contracts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_SQL = "status IN ('submitted','in_progress','ready','rejected','cancelled')"
TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
UUID_SERVER_DEFAULT = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "document_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="submitted",
            nullable=False,
        ),
        sa.Column("document_number", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("processed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
        sa.CheckConstraint(STATUS_SQL, name="status"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_document_requests_school_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["iam.users.id"],
            name="fk_document_requests_requester_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_document_requests_student_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["processed_by_id"],
            ["iam.users.id"],
            name="fk_document_requests_processed_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_requests"),
        schema="documents",
    )
    op.create_index(
        "ix_documents_document_requests_school_id",
        "document_requests",
        ["school_id"],
        schema="documents",
    )
    op.create_index(
        "ix_documents_document_requests_requester_id",
        "document_requests",
        ["requester_id"],
        schema="documents",
    )
    op.create_index(
        "ix_documents_document_requests_student_id",
        "document_requests",
        ["student_id"],
        schema="documents",
    )
    op.create_index(
        "ix_documents_document_requests_school_status",
        "document_requests",
        ["school_id", "status"],
        schema="documents",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_document_requests_school_status",
        table_name="document_requests",
        schema="documents",
    )
    op.drop_index(
        "ix_documents_document_requests_student_id",
        table_name="document_requests",
        schema="documents",
    )
    op.drop_index(
        "ix_documents_document_requests_requester_id",
        table_name="document_requests",
        schema="documents",
    )
    op.drop_index(
        "ix_documents_document_requests_school_id",
        table_name="document_requests",
        schema="documents",
    )
    op.drop_table("document_requests", schema="documents")
