"""Organisation schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    city: str | None
    address: str | None
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    grade: int
    letter: str
    title: str | None
    academic_year: str
    homeroom_teacher_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    display_name: str
