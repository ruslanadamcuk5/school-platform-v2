"""Authentication and user schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID | None
    login: str
    email: str | None
    role: str
    first_name: str
    last_name: str
    middle_name: str | None
    full_name: str
    phone: str | None
    avatar: str
    locale: str
    timezone: str
    is_active: bool
    is_verified: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime


class UserCreate(BaseModel):
    login: str = Field(min_length=2, max_length=120, pattern=r"^[A-Za-z0-9._@+-]+$")
    password: str = Field(min_length=8, max_length=72)
    role: str = Field(default="student")
    first_name: str = Field(default="", max_length=120)
    last_name: str = Field(default="", max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)


class UserList(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


class AdminStats(BaseModel):
    school_id: uuid.UUID
    users_total: int
    users_active: int
    by_role: dict[str, int]
    classes_total: int
    classes_active: int


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict
    ip_address: str | None
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditEventOut]
    limit: int
    offset: int


TokenPair.model_rebuild()
