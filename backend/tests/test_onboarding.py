"""Tests for the personalised onboarding catalogue and API contract."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.onboarding import _module_out
from app.main import app
from app.models.iam import ROLE_VALUES
from app.services.access import EffectivePermissions, ServiceState
from app.services.onboarding import PersonalizedModule, module_is_eligible
from app.services.onboarding_catalog import MODULES, get_module
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE


def _student():
    return SimpleNamespace(id=uuid.uuid4(), role="student")


def test_every_module_targets_a_published_service() -> None:
    for module in MODULES:
        assert module.service_code in SERVICE_BY_CODE
        assert module.steps
        assert len({step.code for step in module.steps}) == len(module.steps)


def test_every_required_permission_is_published() -> None:
    for module in MODULES:
        for code in module.required_permissions:
            assert code in PERMISSION_BY_CODE


def test_module_roles_are_valid() -> None:
    for module in MODULES:
        if module.roles is not None:
            assert set(module.roles) <= set(ROLE_VALUES)


def test_disabled_service_excludes_module() -> None:
    module = get_module("journal-daily")
    assert module is not None
    states = {
        "journal": ServiceState(code="journal", enabled=False, source="test")
    }
    assert not module_is_eligible(
        _student(), module, states, EffectivePermissions(group_count=0)
    )


def test_legacy_permission_allows_student_library_module() -> None:
    module = get_module("library-reading")
    assert module is not None
    states = {
        "library": ServiceState(code="library", enabled=True, source="test")
    }
    assert module_is_eligible(
        _student(), module, states, EffectivePermissions(group_count=0)
    )


def test_role_filter_blocks_admin_training_for_student() -> None:
    module = get_module("admin-school")
    assert module is not None
    states = {
        "admin": ServiceState(code="admin", enabled=True, source="test")
    }
    permissions = EffectivePermissions(group_count=1)
    permissions.allowed["admin.school.read"] = True
    assert not module_is_eligible(_student(), module, states, permissions)


def test_module_payload_contains_step_completion() -> None:
    module = get_module("platform-basics")
    assert module is not None
    progress = SimpleNamespace(
        status="in_progress",
        current_step_code="dashboard",
        completed_step_codes=["dashboard"],
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        last_activity_at=datetime.now(timezone.utc),
    )
    payload = _module_out(
        PersonalizedModule(module=module, progress=progress, is_addon=True)
    )
    assert payload.is_addon is True
    assert payload.completed_steps == 1
    assert payload.steps[0].completed is True
    assert payload.progress_percent > 0


def test_onboarding_routes_are_published() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/onboarding/me" in paths
    assert "/api/v1/onboarding/me/modules/{module_code}" in paths
    assert "/api/v1/onboarding/me/modules/{module_code}/start" in paths
    assert (
        "/api/v1/onboarding/me/modules/{module_code}/steps/{step_code}/complete"
        in paths
    )
    assert "/api/v1/onboarding/reports/summary" in paths
    assert "/api/v1/onboarding/reports/users" in paths
    assert "/api/v1/onboarding/reports/export.csv" in paths
