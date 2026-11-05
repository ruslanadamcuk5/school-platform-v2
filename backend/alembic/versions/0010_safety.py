"""Safety service tables: psychological appeals, incidents, geolocation and consents.

Revision ID: 0010_safety
Revises: 0009_document_requests
Create Date: 2026-11-04

Implemented in accordance with the requirements of the Law of the Republic of
Belarus of 07.05.2021 No. 99-З "On personal data protection" (as amended by
Law No. 134-З of 16.03.2026):

- special personal data (health, incl. psychological) is processed only with
  consent of the subject or their legal representative (Art. 5, Art. 8);
- a minor under 16 may be represented by a legal representative (Art. 5(8));
- storage is limited to the period required for the declared purposes (Art. 4(8));
- the subject may withdraw consent at any time; the operator stops processing
  within 15 days (Art. 10).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_safety"
down_revision: Union[str, None] = "0009_document_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIMESTAMP_SERVER_DEFAULT = sa.text("now()")
UUID_SERVER_DEFAULT = sa.text("gen_random_uuid()")

STATUS_APPEAL_SQL = "status IN ('open','in_progress','responded','closed')"
PRIORITY_SQL = "priority IN ('low','medium','high','urgent')"
CATEGORY_APPEAL_SQL = (
    "category IN ('psychological','conflict','bullying','family','other')"
)
STATUS_INCIDENT_SQL = "status IN ('open','investigating','resolved','closed')"
SEVERITY_SQL = "severity IN ('low','medium','high','critical')"
CATEGORY_INCIDENT_SQL = (
    "category IN ('bullying','violence','self_harm','health','facility','other')"
)
EVENT_TYPE_SQL = "event_type IN ('location','enter_school','leave_school')"
SCOPE_CONSENT_SQL = (
    "scope IN ('geolocation','psychological_support','incident_reporting','health_data')"
)
SOURCE_SQL = "source IN ('written','electronic','verbal_recorded')"
LATITUDE_SQL = "latitude BETWEEN -90 AND 90"
LONGITUDE_SQL = "longitude BETWEEN -180 AND 180"


def upgrade() -> None:
    # Date of birth is needed to apply the minor-consent rule of Law No. 99-З.
    op.add_column(
        "users",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        schema="iam",
    )

    op.create_table(
        "support_appeals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("responded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("consent_required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("consent_given", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
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
        sa.CheckConstraint(STATUS_APPEAL_SQL, name="status"),
        sa.CheckConstraint(PRIORITY_SQL, name="priority"),
        sa.CheckConstraint(CATEGORY_APPEAL_SQL, name="category"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_support_appeals_school_id_schools",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_support_appeals_student_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requester_id"],
            ["iam.users.id"],
            name="fk_support_appeals_requester_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["responded_by_id"],
            ["iam.users.id"],
            name="fk_support_appeals_responded_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_support_appeals"),
        schema="safety",
    )
    op.create_index(
        "ix_safety_support_appeals_school_id",
        "support_appeals",
        ["school_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_support_appeals_student_id",
        "support_appeals",
        ["student_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_support_appeals_requester_id",
        "support_appeals",
        ["requester_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_support_appeals_status",
        "support_appeals",
        ["status"],
        schema="safety",
    )

    op.create_table(
        "incidents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reported_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actions_taken", sa.Text(), nullable=True),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
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
        sa.CheckConstraint(STATUS_INCIDENT_SQL, name="status"),
        sa.CheckConstraint(SEVERITY_SQL, name="severity"),
        sa.CheckConstraint(CATEGORY_INCIDENT_SQL, name="category"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["org.schools.id"],
            name="fk_incidents_school_id_schools",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_id"],
            ["iam.users.id"],
            name="fk_incidents_reported_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["iam.users.id"],
            name="fk_incidents_resolved_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
        schema="safety",
    )
    op.create_index(
        "ix_safety_incidents_school_id",
        "incidents",
        ["school_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_incidents_status",
        "incidents",
        ["status"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_incidents_severity",
        "incidents",
        ["severity"],
        schema="safety",
    )

    op.create_table(
        "geolocation_points",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(6, 2), nullable=True),
        sa.Column("event_type", sa.String(length=24), server_default="location", nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.CheckConstraint(LATITUDE_SQL, name="latitude_range"),
        sa.CheckConstraint(LONGITUDE_SQL, name="longitude_range"),
        sa.CheckConstraint(EVENT_TYPE_SQL, name="event_type"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_geolocation_points_student_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geolocation_points"),
        schema="safety",
    )
    op.create_index(
        "ix_safety_geolocation_points_student_id",
        "geolocation_points",
        ["student_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_geolocation_points_recorded_at",
        "geolocation_points",
        ["recorded_at"],
        schema="safety",
    )

    op.create_table(
        "consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=UUID_SERVER_DEFAULT,
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "legal_representative_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=48), nullable=False),
        sa.Column("granted", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=24), server_default="electronic", nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
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
        sa.CheckConstraint(SCOPE_CONSENT_SQL, name="scope"),
        sa.CheckConstraint(SOURCE_SQL, name="source"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["iam.users.id"],
            name="fk_consents_student_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["legal_representative_id"],
            ["iam.users.id"],
            name="fk_consents_legal_representative_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consents"),
        schema="safety",
    )
    op.create_index(
        "ix_safety_consents_student_id",
        "consents",
        ["student_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_consents_legal_representative_id",
        "consents",
        ["legal_representative_id"],
        schema="safety",
    )
    op.create_index(
        "ix_safety_consents_scope",
        "consents",
        ["scope"],
        schema="safety",
    )

    # geolocation_points was created before consents; add its FK now.
    op.create_foreign_key(
        "fk_geolocation_points_consent_id_consents",
        "geolocation_points",
        "consents",
        ["consent_id"],
        ["id"],
        source_schema="safety",
        referent_schema="safety",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_column("users", "date_of_birth", schema="iam")
    op.drop_constraint(
        "fk_geolocation_points_consent_id_consents",
        "geolocation_points",
        schema="safety",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_safety_consents_scope",
        table_name="consents",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_consents_legal_representative_id",
        table_name="consents",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_consents_student_id",
        table_name="consents",
        schema="safety",
    )
    op.drop_table("consents", schema="safety")
    op.drop_index(
        "ix_safety_geolocation_points_recorded_at",
        table_name="geolocation_points",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_geolocation_points_student_id",
        table_name="geolocation_points",
        schema="safety",
    )
    op.drop_table("geolocation_points", schema="safety")
    op.drop_index(
        "ix_safety_incidents_severity",
        table_name="incidents",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_incidents_status",
        table_name="incidents",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_incidents_school_id",
        table_name="incidents",
        schema="safety",
    )
    op.drop_table("incidents", schema="safety")
    op.drop_index(
        "ix_safety_support_appeals_status",
        table_name="support_appeals",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_support_appeals_requester_id",
        table_name="support_appeals",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_support_appeals_student_id",
        table_name="support_appeals",
        schema="safety",
    )
    op.drop_index(
        "ix_safety_support_appeals_school_id",
        table_name="support_appeals",
        schema="safety",
    )
    op.drop_table("support_appeals", schema="safety")
