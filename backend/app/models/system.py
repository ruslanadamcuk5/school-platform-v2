"""System settings, languages, feature flags and migration bookkeeping."""
from __future__ import annotations

from datetime import datetime

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.scopes import SCOPE_TYPE_SQL
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = {"schema": "system"}

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict | list | str | int | bool | None] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Language(Base):
    __tablename__ = "languages"
    __table_args__ = {"schema": "system"}

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = {"schema": "system"}

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="global", server_default="global"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImportRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "import_runs"
    __table_args__ = {"schema": "system"}

    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="running", server_default="running"
    )
    counts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Service(Base, TimestampMixin):
    """Platform service catalog entry.

    Every functional domain is registered as an independently deployable
    service.  The catalog drives three things at once: which routers are
    mounted by the gateway, which permissions are published to administrators
    and which navigation entries are shown to a user.
    """

    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "category IN ('core','education','management','communication',"
            "'analytics','ai','security')",
            name="category",
        ),
        CheckConstraint(
            "status IN ('active','beta','disabled')", name="status"
        ),
        {"schema": "system"},
    )

    code: Mapped[str] = mapped_column(CITEXT, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="1.0.0", server_default="1.0.0"
    )
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="education", server_default="education"
    )
    api_prefix: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", server_default=""
    )
    icon: Mapped[str] = mapped_column(
        String(32), nullable=False, default="🧩", server_default="🧩"
    )
    default_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_core: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    manifest: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class ServiceActivation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-scope switch that turns a service on or off.

    The access resolver picks the most specific activation for the user's
    scope tree.  A service disabled at school level stays disabled even when
    it is enabled for the whole country.
    """

    __tablename__ = "service_activations"
    __table_args__ = (
        UniqueConstraint(
            "service_code",
            "scope_type",
            "scope_id",
            name="uq_service_activations_service_scope",
        ),
        CheckConstraint(SCOPE_TYPE_SQL, name="scope_type"),
        CheckConstraint("depth BETWEEN 0 AND 4", name="depth_range"),
        Index("ix_system_service_activations_scope", "scope_type", "scope_id"),
        {"schema": "system"},
    )

    service_code: Mapped[str] = mapped_column(
        CITEXT,
        ForeignKey("system.services.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    depth: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
