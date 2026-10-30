"""Unit tests for hierarchical permission and service resolution."""
from __future__ import annotations

import uuid

from app.services.access import (
    PermissionGrant,
    legacy_allows,
    pick_service_state,
    resolve_permissions,
    scope_within,
)
from app.services.registry import PERMISSION_BY_CODE, SERVICES


def _grant(
    code: str,
    *,
    effect: str = "allow",
    depth: int = 3,
    scope_type: str = "school",
    group_id: uuid.UUID | None = None,
) -> PermissionGrant:
    return PermissionGrant(
        code=code,
        effect=effect,
        depth=depth,
        scope_type=scope_type,
        group_id=group_id or uuid.uuid4(),
        group_code=f"group-{depth}",
        group_name=f"Group depth {depth}",
    )


def test_most_specific_scope_wins() -> None:
    access = resolve_permissions(
        [
            _grant("journal.grades.read", depth=0, scope_type="country"),
            _grant(
                "journal.grades.read",
                effect="deny",
                depth=3,
                scope_type="school",
            ),
        ]
    )
    assert access.can("journal.grades.read") is False
    assert access.grants["journal.grades.read"].scope_type == "school"


def test_class_allow_overrides_school_deny() -> None:
    access = resolve_permissions(
        [
            _grant("journal.grades.read", effect="deny", depth=3),
            _grant(
                "journal.grades.read",
                depth=4,
                scope_type="class",
            ),
        ]
    )
    assert access.can("journal.grades.read") is True
    assert access.grants["journal.grades.read"].scope_type == "class"


def test_deny_wins_on_the_same_depth() -> None:
    access = resolve_permissions(
        [
            _grant("library.books.manage", depth=3),
            _grant("library.books.manage", effect="deny", depth=3),
        ]
    )
    assert access.can("library.books.manage") is False


def test_unknown_permission_is_not_granted() -> None:
    access = resolve_permissions([])
    assert access.can("journal.grades.write") is False


def test_core_service_is_always_enabled() -> None:
    state = pick_service_state(
        "iam", default_enabled=False, is_core=True, activations=[]
    )
    assert state.enabled is True
    assert state.source == "core"


def test_service_default_applies_without_activation() -> None:
    state = pick_service_state(
        "documents", default_enabled=False, is_core=False, activations=[]
    )
    assert state.enabled is False
    assert state.source == "default"


def test_school_can_disable_country_enabled_service() -> None:
    country = _activation("library", depth=0, scope_type="country", enabled=True)
    school = _activation("library", depth=3, scope_type="school", enabled=False)
    state = pick_service_state(
        "library", default_enabled=False, is_core=False, activations=[country, school]
    )
    assert state.enabled is False
    assert state.source == "activation"
    assert state.scope_type == "school"


def test_school_can_enable_country_disabled_service() -> None:
    country = _activation("ai", depth=0, scope_type="country", enabled=False)
    school = _activation("ai", depth=3, scope_type="school", enabled=True)
    state = pick_service_state(
        "ai", default_enabled=False, is_core=False, activations=[country, school]
    )
    assert state.enabled is True
    assert state.scope_type == "school"


def _activation(code: str, *, depth: int, scope_type: str, enabled: bool):
    from types import SimpleNamespace

    return SimpleNamespace(
        service_code=code,
        depth=depth,
        scope_type=scope_type,
        scope_id=uuid.uuid4(),
        enabled=enabled,
        config={},
    )


def test_legacy_bridge_is_explicit() -> None:
    assert legacy_allows("admin", "iam.groups.write") is True
    assert legacy_allows("student", "iam.groups.write") is False
    assert legacy_allows("teacher", "journal.grades.write") is True
    assert legacy_allows("parent", "journal.grades.write") is False


def test_scope_within_rejects_unrelated_scope() -> None:
    school_id = uuid.uuid4()
    region_id = uuid.uuid4()
    ancestors = {("country", uuid.UUID(int=0)), ("region", region_id), ("school", school_id)}
    assert scope_within(("school", school_id), ancestors) is True
    assert scope_within(("school", uuid.uuid4()), ancestors) is False


def test_registry_permissions_are_unique_and_namespaced() -> None:
    codes = [permission.code for manifest in SERVICES for permission in manifest.permissions]
    assert len(codes) == len(set(codes))
    assert len(codes) == len(PERMISSION_BY_CODE)
    for manifest in SERVICES:
        for permission in manifest.permissions:
            assert permission.code.startswith(f"{manifest.code}.")
