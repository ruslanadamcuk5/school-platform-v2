"""Schemas for the platform service catalog and per-scope activations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScopeType = Literal["country", "region", "city", "school", "class"]
ServiceCategory = Literal[
    "core", "education", "management", "communication", "analytics", "ai", "security"
]
ServiceStatus = Literal["active", "beta", "disabled"]


class ServicePermissionOut(BaseModel):
    code: str
    name: str
    category: str


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str | None = None
    version: str
    category: ServiceCategory
    api_prefix: str
    icon: str
    default_enabled: bool
    is_core: bool
    status: ServiceStatus
    manifest: dict = Field(default_factory=dict)


class ServiceListOut(BaseModel):
    items: list[ServiceOut]
    total: int


class ServiceActivationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_code: str
    scope_type: ScopeType
    scope_id: uuid.UUID
    depth: int
    enabled: bool
    config: dict = Field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    updated_at: datetime


class ServiceActivationSet(BaseModel):
    enabled: bool
    config: dict = Field(default_factory=dict)


class EffectiveServiceOut(BaseModel):
    code: str
    name: str
    description: str | None = None
    icon: str
    category: ServiceCategory
    api_prefix: str
    status: ServiceStatus
    enabled: bool
    source: Literal["core", "activation", "default"]
    permission_codes: list[str] = Field(default_factory=list)


class MyServicesOut(BaseModel):
    items: list[EffectiveServiceOut]
    total: int
