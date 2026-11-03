"""Personalised platform onboarding and training progress."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PROGRESS_STATUSES = ("not_started", "in_progress", "completed", "skipped")


class OnboardingProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-user state of the personalised training programme.

    ``known_service_codes`` records which services were already part of the
    curriculum when the learner last interacted with it.  A service enabled
    later is shown as an "add-on" module until the learner starts it.
    """

    __tablename__ = "profiles"
    __table_args__ = ({"schema": "onboarding"},)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    known_service_codes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    catalog_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="1.0.0", server_default="1.0.0"
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OnboardingModuleProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Progress through one personalised training module."""

    __tablename__ = "module_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "module_code", name="uq_module_progress_user_module"
        ),
        CheckConstraint(
            "status IN ('not_started','in_progress','completed','skipped')",
            name="status",
        ),
        Index("ix_onboarding_module_progress_user", "user_id"),
        Index("ix_onboarding_module_progress_service", "service_code"),
        {"schema": "onboarding"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_code: Mapped[str] = mapped_column(String(128), nullable=False)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_started", server_default="not_started"
    )
    current_step_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    completed_step_codes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
