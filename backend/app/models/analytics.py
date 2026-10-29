"""Analytics aggregates for practice attempts and topic progress."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.iam import User
    from app.models.lms import Method, Topic


class Attempt(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "attempts"
    __table_args__ = {"schema": "analytics"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    method_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.methods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    given_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hints_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="practice", server_default="practice"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    topic: Mapped["Topic | None"] = relationship()
    method: Mapped["Method | None"] = relationship()


class TopicProgress(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "topic_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_topic_progress_user_topic"),
        {"schema": "analytics"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stars: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    best_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    best_accuracy: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, server_default="0"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    boss_cleared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship()
    topic: Mapped["Topic"] = relationship()


class MethodProgress(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "method_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "method_id", name="uq_method_progress_user_method"),
        {"schema": "analytics"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lms.methods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seen: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    mastered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship()
    method: Mapped["Method"] = relationship()


class DailyAnswer(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "daily_answers"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "day", "generator", name="uq_daily_answers_user_day_generator"
        ),
        {"schema": "analytics"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    generator: Mapped[str] = mapped_column(String(128), nullable=False)
    correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
