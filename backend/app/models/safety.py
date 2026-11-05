"""Safety service models: psychological appeals, incidents, geolocation and consents.

Implemented with due regard to the Law of the Republic of Belarus of
07.05.2021 No. 99-З "On personal data protection" (as amended by Law
No. 134-З of 16.03.2026):

- special personal data (health, incl. psychological state) is processed only
  with the consent of the subject or their legal representative (Art. 5, Art. 8);
- a minor under 16 may be represented by a legal representative (Art. 5(8));
- storage is limited to the period required for the declared purposes
  (Art. 4(8)) — retention is configurable per school activation;
- the subject may withdraw consent at any time; the operator stops processing
  within 15 days (Art. 10).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

APPEAL_STATUS_SQL = "status IN ('open','in_progress','responded','closed')"
APPEAL_PRIORITY_SQL = "priority IN ('low','medium','high','urgent')"
APPEAL_CATEGORY_SQL = (
    "category IN ('psychological','conflict','bullying','family','other')"
)

APPEAL_STATUSES = ("open", "in_progress", "responded", "closed")
INCIDENT_STATUSES = ("open", "investigating", "resolved", "closed")

INCIDENT_STATUS_SQL = "status IN ('open','investigating','resolved','closed')"
INCIDENT_SEVERITY_SQL = "severity IN ('low','medium','high','critical')"
INCIDENT_CATEGORY_SQL = (
    "category IN ('bullying','violence','self_harm','health','facility','other')"
)

GEOLOCATION_EVENT_TYPE_SQL = "event_type IN ('location','enter_school','leave_school')"
LATITUDE_SQL = "latitude BETWEEN -90 AND 90"
LONGITUDE_SQL = "longitude BETWEEN -180 AND 180"

CONSENT_SCOPE_SQL = (
    "scope IN ('geolocation','psychological_support','incident_reporting','health_data')"
)
CONSENT_SOURCE_SQL = "source IN ('written','electronic','verbal_recorded')"


class SupportAppeal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A psychological support appeal from a student, parent or anonymously."""

    __tablename__ = "support_appeals"
    __table_args__ = (
        CheckConstraint(APPEAL_STATUS_SQL, name="status"),
        CheckConstraint(APPEAL_PRIORITY_SQL, name="priority"),
        CheckConstraint(APPEAL_CATEGORY_SQL, name="category"),
        {"schema": "safety"},
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requester_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium", server_default="medium"
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="open", server_default="open"
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_anonymous: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    consent_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    consent_given: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A safety incident registered for a school."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(INCIDENT_STATUS_SQL, name="status"),
        CheckConstraint(INCIDENT_SEVERITY_SQL, name="severity"),
        CheckConstraint(INCIDENT_CATEGORY_SQL, name="category"),
        {"schema": "safety"},
    )

    school_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="open", server_default="open"
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actions_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GeolocationPoint(Base, UUIDPrimaryKeyMixin):
    """A geolocation point for a student, bound to an active consent."""

    __tablename__ = "geolocation_points"
    __table_args__ = (
        CheckConstraint(LATITUDE_SQL, name="latitude_range"),
        CheckConstraint(LONGITUDE_SQL, name="longitude_range"),
        CheckConstraint(GEOLOCATION_EVENT_TYPE_SQL, name="event_type"),
        {"schema": "safety"},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="location", server_default="location"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("safety.consents.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Consent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Consent of a legal representative for processing a student's data."""

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(CONSENT_SCOPE_SQL, name="scope"),
        CheckConstraint(CONSENT_SOURCE_SQL, name="source"),
        {"schema": "safety"},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_representative_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(48), nullable=False)
    granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(24), nullable=False, default="electronic", server_default="electronic"
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
