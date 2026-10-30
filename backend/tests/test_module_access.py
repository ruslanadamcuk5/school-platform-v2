"""Route-level checks for service activation and group permissions."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.api.deps import get_current_user
from app.db.session import get_session
from app.main import app
from app.services.access import EffectivePermissions, ServiceState


async def _request(path: str):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role="teacher",
        school_id=uuid.uuid4(),
        is_active=True,
        deleted_at=None,
    )

    async def override_user():
        return user

    async def override_session():
        yield object()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(path)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "service"),
    [
        ("/api/v1/journal/schedule", "journal"),
        ("/api/v1/assessment/assignments", "assessment"),
        ("/api/v1/library", "library"),
        ("/api/v1/lms/subjects", "lms"),
    ],
)
async def test_module_rejects_disabled_service(monkeypatch, path, service):
    async def disabled_states(_session, _user):
        return {
            service: ServiceState(
                code=service,
                enabled=False,
                source="test",
            )
        }

    monkeypatch.setattr(deps, "user_service_states", disabled_states)
    response = await _request(path)
    assert response.status_code == 403
    assert service in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "service"),
    [
        ("/api/v1/journal/schedule", "journal"),
        ("/api/v1/assessment/assignments", "assessment"),
        ("/api/v1/library", "library"),
        ("/api/v1/lms/subjects", "lms"),
    ],
)
async def test_module_rejects_missing_permission(monkeypatch, path, service):
    async def enabled_states(_session, _user):
        return {
            service: ServiceState(
                code=service,
                enabled=True,
                source="test",
            )
        }

    async def no_permissions(_session, _user):
        return EffectivePermissions(group_count=1)

    monkeypatch.setattr(deps, "user_service_states", enabled_states)
    monkeypatch.setattr(deps, "effective_permissions", no_permissions)
    response = await _request(path)
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]
