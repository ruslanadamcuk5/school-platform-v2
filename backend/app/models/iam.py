"""IAM models: users, roles and refresh sessions."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.org import School

ROLE_VALUES = (
    "superadmin",
    "admin",
    "methodologist",
    "teacher",
    "student",
    "parent",
    "psychologist",
    "secretary",
)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('superadmin','admin','methodologist','teacher','student',"
            "'parent','psychologist','secretary')",
            name="role",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
        {"schema": "iam"},
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("org.schools.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    login: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(
        CITEXT, nullable=True, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="student",
        server_default="student",
        index=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(120), nullable=False, default="", server_default=""
    )
    last_name: Mapped[str] = mapped_column(
        String(120), nullable=False, default="", server_default=""
    )
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_code: Mapped[str | None] = mapped_column(
        String(16), nullable=True, unique=True, index=True
    )
    avatar: Mapped[str] = mapped_column(
        String(32), nullable=False, default="👤", server_default="👤"
    )
    locale: Mapped[str] = mapped_column(
        String(8), nullable=False, default="ru", server_default="ru"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Europe/Minsk", server_default="Europe/Minsk"
    )
    preferences: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    school: Mapped["School | None"] = relationship(
        back_populates="users", foreign_keys=[school_id]
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    child_relations: Mapped[list["UserRelation"]] = relationship(
        back_populates="parent",
        foreign_keys="UserRelation.parent_id",
        cascade="all, delete-orphan",
    )
    parent_relations: Mapped[list["UserRelation"]] = relationship(
        back_populates="child",
        foreign_keys="UserRelation.child_id",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part).strip()

    @property
    def is_superadmin(self) -> bool:
        return self.role == "superadmin"


class UserRelation(Base, UUIDPrimaryKeyMixin):
    """Parent/guardian to child relation."""

    __tablename__ = "user_relations"
    __table_args__ = (
        UniqueConstraint("parent_id", "child_id", name="uq_user_relations_parent_child"),
        CheckConstraint(
            "relation_type IN ('mother','father','guardian','other')",
            name="relation_type",
        ),
        {"schema": "iam"},
    )

    parent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="other", server_default="other"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parent: Mapped["User"] = relationship(
        back_populates="child_relations", foreign_keys=[parent_id]
    )
    child: Mapped["User"] = relationship(
        back_populates="parent_relations", foreign_keys=[child_id]
    )


class RefreshToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "iam"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.now(
            self.expires_at.tzinfo
        )
