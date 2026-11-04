"""Documents schemas: secretariat requests."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentRequestCreate(BaseModel):
    school_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    document_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("document_type", "title")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

    @field_validator("reason")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DocumentRequestProcess(BaseModel):
    status: Literal["in_progress", "ready", "rejected"]
    document_number: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("document_number", "comment")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_document_number(self) -> "DocumentRequestProcess":
        if self.status == "ready" and self.document_number is None:
            raise ValueError("Document number is required when a request is ready")
        if self.status != "ready" and self.document_number is not None:
            raise ValueError("Document number is only allowed for a ready request")
        return self


class DocumentRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    requester_id: uuid.UUID
    student_id: uuid.UUID | None
    document_type: str
    title: str
    reason: str | None
    status: str
    document_number: str | None
    comment: str | None
    processed_by_id: uuid.UUID | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime
