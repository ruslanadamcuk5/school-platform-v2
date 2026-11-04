"""Communication schemas: in-app notifications."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=5000)
    notification_type: str = Field(default="system", min_length=1, max_length=64)
    channel: Literal["in_app"] = "in_app"
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "notification_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

    @field_validator("body")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    notification_type: str
    title: str
    body: str | None
    payload: dict[str, Any]
    read_at: datetime | None
    sent_at: datetime | None
    status: str
    created_at: datetime
