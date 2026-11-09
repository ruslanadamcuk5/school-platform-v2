"""Runtime platform settings and the superadmin cache console API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api import deps
from app.api.deps import get_current_user
from app.api.v1 import admin_settings
from app.core.config import settings
from app.db.session import get_session
from app.main import app
from app.schemas.platform_settings import CacheSettingsUpdate
from app.services.access import EffectivePermissions
from app.services.platform_settings import CacheRuntimeSettings, _coerce


class FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class FakeSession:
    def __init__(self, rows: list[object] | None = None) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.rows = rows or []

    async def get(self, _model, _key):
        return None

    async def execute(self, _statement):
        return FakeResult(self.rows)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def _runtime(
    *,
    enabled: bool = True,
    ttl_seconds: int = 90,
    source: str = "database",
) -> CacheRuntimeSettings:
    return CacheRuntimeSettings(
        enabled=enabled,
        ttl_seconds=ttl_seconds,
        key_prefix="school-platform",
        socket_timeout_seconds=1.0,
        failure_cooldown_seconds=30.0,
        source=source,
    )


def test_cache_update_validates_bounds_and_prefix() -> None:
    assert CacheSettingsUpdate(ttl_seconds=60).ttl_seconds == 60
    assert CacheSettingsUpdate(key_prefix="school-platform").key_prefix
    with pytest.raises(ValidationError):
        CacheSettingsUpdate(ttl_seconds=4)
    with pytest.raises(ValidationError):
        CacheSettingsUpdate(socket_timeout_seconds=0)
    with pytest.raises(ValidationError):
        CacheSettingsUpdate(key_prefix="bad prefix")


def test_runtime_coercion_rejects_invalid_stored_values(monkeypatch) -> None:
    monkeypatch.setattr(settings, "redis_url", "rediss://redis.example:6380/0")
    monkeypatch.setattr(settings, "redis_cache_ttl_seconds", 60)
    monkeypatch.setattr(settings, "redis_key_prefix", "school-platform")
    monkeypatch.setattr(settings, "redis_socket_timeout_seconds", 1.0)
    monkeypatch.setattr(settings, "redis_failure_cooldown_seconds", 30.0)

    runtime = _coerce(
        {
            "enabled": "yes",
            "ttl_seconds": 99999,
            "key_prefix": "bad prefix",
            "socket_timeout_seconds": 0,
            "failure_cooldown_seconds": -1,
        }
    )

    assert runtime.enabled is True
    assert runtime.ttl_seconds == 60
    assert runtime.key_prefix == "school-platform"
    assert runtime.socket_timeout_seconds == 1.0
    assert runtime.failure_cooldown_seconds == 30.0
    assert runtime.source == "database"


def _override_user(role: str):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        school_id=None,
        is_active=True,
        deleted_at=None,
    )

    async def override_user():
        return user

    return user, override_user


def _override_session(session: FakeSession):
    async def override_session():
        yield session

    return override_session


def _allow(permission: str):
    async def effective_permissions(_session, _user):
        return EffectivePermissions(
            group_count=1,
            allowed={permission: True},
        )

    return effective_permissions


@pytest.mark.asyncio
async def test_cache_console_requires_superadmin(monkeypatch) -> None:
    _user, override_user = _override_user("admin")
    session = FakeSession()
    monkeypatch.setattr(deps, "effective_permissions", _allow("system.settings.read"))
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/admin/settings/cache")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cache_console_returns_masked_state(monkeypatch) -> None:
    monkeypatch.setattr(settings, "redis_url", "rediss://redis.example:6380/0")
    _user, override_user = _override_user("superadmin")
    session = FakeSession()
    runtime = _runtime()

    async def fake_runtime(*_args, **_kwargs):
        return runtime

    async def fake_ping():
        return True

    monkeypatch.setattr(deps, "effective_permissions", _allow("system.settings.read"))
    monkeypatch.setattr(admin_settings, "get_cache_runtime", fake_runtime)
    monkeypatch.setattr(admin_settings, "cache_ping", fake_ping)
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/admin/settings/cache")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["mode"] == "managed-redis-tls"
    assert payload["endpoint_configured"] is True
    assert payload["tls_enabled"] is True
    assert payload["fail_open"] is True
    assert "redis.example" not in response.text
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_cache_update_rejects_enable_without_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "redis_url", None)
    _user, override_user = _override_user("superadmin")
    session = FakeSession()
    monkeypatch.setattr(deps, "effective_permissions", _allow("system.settings.write"))
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/v1/admin/settings/cache",
                json={"enabled": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert session.commits == 0


@pytest.mark.asyncio
async def test_cache_update_persists_and_audits(monkeypatch) -> None:
    monkeypatch.setattr(settings, "redis_url", "rediss://redis.example:6380/0")
    _user, override_user = _override_user("superadmin")
    session = FakeSession()
    runtime = _runtime(ttl_seconds=90)

    async def fake_runtime(*_args, **_kwargs):
        return runtime

    async def fake_apply():
        return runtime

    async def fake_ping():
        return True

    monkeypatch.setattr(deps, "effective_permissions", _allow("system.settings.write"))
    monkeypatch.setattr(admin_settings, "get_cache_runtime", fake_runtime)
    monkeypatch.setattr(admin_settings, "apply_cache_runtime_settings", fake_apply)
    monkeypatch.setattr(admin_settings, "cache_ping", fake_ping)
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/v1/admin/settings/cache",
                json={"ttl_seconds": 90, "failure_cooldown_seconds": 20},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ttl_seconds"] == 90
    assert session.commits == 1
    assert len(session.added) == 2
    setting = session.added[0]
    audit = session.added[1]
    assert setting.key == "cache.runtime"
    assert setting.value["ttl_seconds"] == 90
    assert audit.action == "platform.cache.settings.update"
    assert "ttl_seconds" in audit.details["updated"]
    assert audit.details["before"]["ttl_seconds"] == 90
    assert audit.details["after"]["ttl_seconds"] == 90


def _patch_dangerous(monkeypatch, payload: dict, *, permission: str = "system.settings.write"):
    monkeypatch.setattr(settings, "redis_url", "rediss://redis.example:6380/0")
    _user, override_user = _override_user("superadmin")
    session = FakeSession()
    runtime = _runtime(enabled=True)

    async def fake_runtime(*_args, **_kwargs):
        return runtime

    async def fake_apply():
        return runtime

    async def fake_ping():
        return True

    monkeypatch.setattr(deps, "effective_permissions", _allow(permission))
    monkeypatch.setattr(admin_settings, "get_cache_runtime", fake_runtime)
    monkeypatch.setattr(admin_settings, "apply_cache_runtime_settings", fake_apply)
    monkeypatch.setattr(admin_settings, "cache_ping", fake_ping)
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)

    async def call():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.patch(
                "/api/v1/admin/settings/cache",
                json=payload,
            )

    return call, session


@pytest.mark.asyncio
async def test_cache_update_requires_confirmation_for_disable(monkeypatch) -> None:
    call, session = _patch_dangerous(monkeypatch, {"enabled": False})
    try:
        response = await call()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 428
    assert session.commits == 0
    assert "Confirmation required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cache_update_requires_confirmation_for_prefix_change(monkeypatch) -> None:
    call, session = _patch_dangerous(
        monkeypatch,
        {"key_prefix": "school-platform-v2"},
    )
    try:
        response = await call()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 428
    assert session.commits == 0
    assert "Confirmation required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cache_update_requires_reason_for_dangerous_change(monkeypatch) -> None:
    call, session = _patch_dangerous(
        monkeypatch,
        {"enabled": False, "confirm": True},
    )
    try:
        response = await call()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert session.commits == 0


@pytest.mark.asyncio
async def test_cache_update_confirms_dangerous_change_and_audits_reason(monkeypatch) -> None:
    call, session = _patch_dangerous(
        monkeypatch,
        {
            "enabled": False,
            "confirm": True,
            "reason": "Плановое отключение на время диагностики",
        },
    )
    try:
        response = await call()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert session.commits == 1
    audit = session.added[1]
    assert audit.details["before"]["enabled"] is True
    assert audit.details["after"]["enabled"] is False
    assert audit.details["reason"] == "Плановое отключение на время диагностики"
    assert audit.details["confirmed_dangerous"] is True


@pytest.mark.asyncio
async def test_cache_history_returns_audit_events(monkeypatch) -> None:
    event = SimpleNamespace(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        user_id=uuid.uuid4(),
        action="platform.cache.settings.update",
        details={
            "updated": ["ttl_seconds"],
            "before": {"ttl_seconds": 60},
            "after": {"ttl_seconds": 120},
            "reason": "Увеличение TTL",
            "confirmed_dangerous": False,
        },
    )
    session = FakeSession(rows=[(event, "superadmin")])
    _user, override_user = _override_user("superadmin")
    monkeypatch.setattr(deps, "effective_permissions", _allow("system.settings.read"))
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = _override_session(session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/admin/settings/cache/history")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["user_login"] == "superadmin"
    assert payload["items"][0]["details"]["reason"] == "Увеличение TTL"
    assert payload["items"][0]["details"]["after"]["ttl_seconds"] == 120
