"""Schemas for hierarchical user groups and permissions."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScopeType = Literal["country", "region", "city", "school", "class"]
GroupCategory = Literal[
    "students",
    "teachers",
    "administration",
    "methodologists",
    "psychologists",
    "secretaries",
    "parents",
    "other",
]
PermissionEffect = Literal["allow", "deny"]
PermissionCategory = Literal["read", "write", "admin", "use"]


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    service_code: str
    category: PermissionCategory
    is_system: bool


class PermissionListOut(BaseModel):
    items: list[PermissionOut]
    total: int


class GroupMemberOut(BaseModel):
    user_id: uuid.UUID
    login: str
    full_name: str
    role: str
    assigned_at: datetime
    expires_at: datetime | None = None
    is_primary: bool = False


class GroupPermissionOut(BaseModel):
    permission_code: str
    permission_name: str
    effect: PermissionEffect
    granted_at: datetime
    expires_at: datetime | None = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    category: GroupCategory
    scope_type: ScopeType
    scope_id: uuid.UUID
    depth: int
    parent_id: uuid.UUID | None = None
    is_system: bool
    is_active: bool
    members_count: int = 0
    permissions_count: int = 0
    created_at: datetime


class GroupDetailOut(GroupOut):
    members: list[GroupMemberOut] = Field(default_factory=list)
    permissions: list[GroupPermissionOut] = Field(default_factory=list)
    children: list[GroupOut] = Field(default_factory=list)


class GroupListOut(BaseModel):
    items: list[GroupOut]
    total: int


class GroupCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.:-]*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: GroupCategory = "other"
    scope_type: ScopeType
    scope_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_system: bool = False
    meta: dict = Field(default_factory=dict)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: GroupCategory | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None
    meta: dict | None = None


class GroupMembersAdd(BaseModel):
    user_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    expires_at: datetime | None = None
    is_primary: bool = False


class GroupPermissionSet(BaseModel):
    effect: PermissionEffect = "allow"
    expires_at: datetime | None = None


class EffectivePermissionOut(BaseModel):
    code: str
    allowed: bool
    effect: PermissionEffect
    scope_type: ScopeType
    group_id: uuid.UUID
    group_code: str
    group_name: str
    depth: int


class MyPermissionsOut(BaseModel):
    user_id: uuid.UUID
    role: str
    permissions: list[str]
    denied: list[str]
    details: list[EffectivePermissionOut]
    groups: list[GroupOut] = Field(default_factory=list)


class GroupStatusOut(BaseModel):
    ok: bool = True
    message: str | None = None
