"""Create PostgreSQL schemas used by the platform.

Revision ID: 0000_schemas
Revises:
Create Date: 2026-10-27

The schemas are created separately so a fresh database can be provisioned with
``alembic upgrade head``. The pilot database already had the schemas and had
0001 applied before this revision was introduced; Alembic treats 0000 as an
ancestor of the current revision and does not replay it.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0000_schemas"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMAS = (
    "iam",
    "org",
    "lms",
    "assessment",
    "journal",
    "communication",
    "safety",
    "documents",
    "analytics",
    "ai",
    "audit",
    "system",
)


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def downgrade() -> None:
    # Schemas are shared by several revisions and are intentionally left in
    # place; dropping them here could destroy data when downgrading one step.
    pass
