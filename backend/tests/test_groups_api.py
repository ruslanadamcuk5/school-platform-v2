"""Tests for the group-based access API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.groups import _group_detail, _group_out, _resolve_scope
from app.core.scopes import COUNTRY_SCOPE_ID
from app.schemas.groups import GroupCreate


def _group(**overrides):
    base = SimpleNamespace(
        id=uuid.uuid4(),
        code="teachers",
        name="Учителя",
        description=None,
        category="teachers",
        scope_type="school",
        scope_id=uuid.uuid4(),
        depth=3,
        parent_id=None,
        is_system=True,
        is_active=True,
        memberships=[],
        permission_links=[],
        children=[],
        created_at=datetime.now(timezone.utc),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_group_out_counts_members_and_permissions() -> None:
    group = _group(
        memberships=[SimpleNamespace()],
        permission_links=[SimpleNamespace(), SimpleNamespace()],
    )
    payload = _group_out(group)
    assert payload.members_count == 1
    assert payload.permissions_count == 2
    assert payload.scope_type == "school"


def test_group_detail_sorts_members_and_permissions() -> None:
    user_a = SimpleNamespace(login="a", full_name="Анна", role="teacher")
    user_b = SimpleNamespace(login="b", full_name="Борис", role="teacher")
    group = _group(
        memberships=[
            SimpleNamespace(
                user_id=uuid.uuid4(),
                user=user_b,
                assigned_at=datetime.now(timezone.utc),
                expires_at=None,
                is_primary=False,
            ),
            SimpleNamespace(
                user_id=uuid.uuid4(),
                user=user_a,
                assigned_at=datetime.now(timezone.utc),
                expires_at=None,
                is_primary=True,
            ),
        ],
        permission_links=[
            SimpleNamespace(
                permission=SimpleNamespace(code="journal.grades.read", name="Чтение"),
                effect="allow",
                granted_at=datetime.now(timezone.utc),
                expires_at=None,
            )
        ],
    )
    detail = _group_detail(group)
    assert [member.full_name for member in detail.members] == ["Анна", "Борис"]
    assert detail.permissions[0].permission_code == "journal.grades.read"


def test_group_detail_includes_child_counts() -> None:
    child = _group(
        code="school.teachers",
        name="Учителя школы",
        memberships=[SimpleNamespace()],
        permission_links=[SimpleNamespace(), SimpleNamespace()],
    )
    group = _group(scope_type="country", children=[child])
    detail = _group_detail(group)
    assert detail.children[0].members_count == 1
    assert detail.children[0].permissions_count == 2


def test_country_scope_uses_fixed_identifier() -> None:
    payload = GroupCreate(
        code="administration",
        name="Администрация",
        category="administration",
        scope_type="country",
    )
    scope_type, scope_id = _resolve_scope(payload)
    assert scope_type == "country"
    assert scope_id == COUNTRY_SCOPE_ID


def test_non_country_scope_requires_identifier() -> None:
    payload = GroupCreate(
        code="teachers",
        name="Учителя",
        category="teachers",
        scope_type="school",
    )
    with pytest.raises(HTTPException) as exc:
        _resolve_scope(payload)
    assert exc.value.status_code == 422


def test_groups_endpoints_are_published() -> None:
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/groups" in paths
    assert "/api/v1/groups/{group_id}" in paths
    assert "/api/v1/groups/permissions" in paths
    assert "/api/v1/groups/{group_id}/members" in paths
    assert "/api/v1/groups/{group_id}/permissions/{permission_code}" in paths
    assert "/api/v1/me/permissions" in paths
    assert "/api/v1/me/services" in paths
