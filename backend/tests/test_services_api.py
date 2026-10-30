"""Tests for the service catalog and activation API."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.services import (
    _fallback_services,
    _resolve_scope,
    effective_services,
    get_service,
    set_activation,
)
from app.core.scopes import COUNTRY_SCOPE_ID
from app.schemas.services import ServiceActivationSet


class FakeResult:
    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return self._items

    def scalar_one_or_none(self):
        return self._scalar


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []

    async def execute(self, _stmt):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def rollback(self):
        return None


def _user(role: str = "superadmin"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        school_id=None,
        full_name="Администратор",
        login="admin",
        is_active=True,
        deleted_at=None,
    )


def test_country_scope_is_resolved() -> None:
    assert _resolve_scope("country", None) == ("country", COUNTRY_SCOPE_ID)


def test_unknown_scope_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        _resolve_scope("planet", None)
    assert exc.value.status_code == 422


def test_fallback_catalog_contains_every_manifest() -> None:
    services = _fallback_services()
    codes = {service.code for service in services}
    assert {"iam", "org", "lms", "journal", "library", "ai"} <= codes


@pytest.mark.asyncio
async def test_get_service_uses_manifest_fallback() -> None:
    session = FakeSession([FakeResult(items=[])])
    service = await get_service("library", _user(), session)
    assert service.code == "library"
    assert service.api_prefix == "/api/v1/library"


@pytest.mark.asyncio
async def test_core_service_cannot_be_disabled() -> None:
    session = FakeSession([FakeResult(scalar=None)])
    with pytest.raises(HTTPException) as exc:
        await set_activation(
            "iam",
            ServiceActivationSet(enabled=False),
            _user(),
            session,
            "country",
            None,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_optional_service_can_be_enabled_for_country() -> None:
    session = FakeSession(
        [
            FakeResult(scalar=None),  # service row
            FakeResult(scalar=None),  # existing activation
        ]
    )
    activation = await set_activation(
        "library",
        ServiceActivationSet(enabled=True, config={"max_books": 50}),
        _user(),
        session,
        "country",
        None,
    )
    assert activation.service_code == "library"
    assert activation.enabled is True
    assert activation.scope_id == COUNTRY_SCOPE_ID
    assert session.added


@pytest.mark.asyncio
async def test_unknown_service_is_rejected() -> None:
    session = FakeSession([FakeResult(scalar=None)])
    with pytest.raises(HTTPException) as exc:
        await set_activation(
            "unknown",
            ServiceActivationSet(enabled=True),
            _user(),
            session,
            "country",
            None,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_effective_services_for_country_returns_catalog() -> None:
    session = FakeSession(
        [
            FakeResult(items=[]),  # activation chain
            FakeResult(items=[]),  # service catalog -> fallback
        ]
    )
    response = await effective_services(
        _user(), session, scope_type="country", scope_id=None
    )
    assert response.total > 0
    codes = {item.code for item in response.items}
    assert "iam" in codes
