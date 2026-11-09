"""Schemas for operational platform settings."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

CacheMode = Literal["disabled", "redis", "managed-redis-tls"]
CacheStatus = Literal["disabled", "connected", "unavailable"]


class CacheSettingsOut(BaseModel):
    enabled: bool
    effective_enabled: bool
    mode: CacheMode
    endpoint_configured: bool
    tls_enabled: bool
    ttl_seconds: int
    key_prefix: str
    socket_timeout_seconds: float
    failure_cooldown_seconds: float
    fail_open: bool
    invalidation: Literal["version"]
    source: Literal["env", "database"]
    status: CacheStatus
    latency_ms: float | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None
    requires_restart: bool = False


class CacheSettingsUpdate(BaseModel):
    enabled: bool | None = None
    ttl_seconds: int | None = Field(default=None, ge=5, le=3600)
    key_prefix: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:_.-]{0,63}$",
    )
    socket_timeout_seconds: float | None = Field(
        default=None, ge=0.1, le=10.0
    )
    failure_cooldown_seconds: float | None = Field(
        default=None, ge=1.0, le=300.0
    )
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=500)


class CacheSettingsHistoryItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None = None
    user_login: str | None = None
    action: str
    details: dict[str, Any]


class CacheSettingsHistory(BaseModel):
    items: list[CacheSettingsHistoryItem]
    limit: int
    offset: int


class CacheTestOut(BaseModel):
    ok: bool
    status: CacheStatus
    mode: CacheMode
    latency_ms: float | None = None
    message: str
