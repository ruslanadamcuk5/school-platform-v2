"""Tests for the optional Redis access cache."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from redis.exceptions import RedisError

from app.core import cache as cache_module
from app.core.cache import (
    access_cache_key,
    access_version,
    bump_access_version,
    get_json,
    reset_cache_for_tests,
    set_json,
)
from app.core.config import Settings
from app.services import access as access_module
from app.services.access import (
    EffectivePermissions,
    PermissionGrant,
    ServiceState,
    _permissions_from_cache,
    _permissions_to_cache,
    _service_states_from_cache,
    _service_states_to_cache,
    effective_permissions,
)


class FakeCache:
    enabled = True

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ttl: int | None) -> None:
        self.data[key] = value
        self.ttls[key] = ttl

    async def incr(self, key: str) -> int:
        value = int(self.data.get(key, "0")) + 1
        self.data[key] = str(value)
        return value

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


class BrokenCache(FakeCache):
    async def get(self, _key: str) -> str | None:
        raise RedisError("redis is down")

    async def set(self, _key: str, _value: str, _ttl: int | None) -> None:
        raise RedisError("redis is down")

    async def incr(self, _key: str) -> int:
        raise RedisError("redis is down")


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


@pytest.mark.asyncio
async def test_cache_is_disabled_without_url(monkeypatch) -> None:
    monkeypatch.setattr(cache_module.settings, "redis_url", None)
    reset_cache_for_tests()

    assert cache_module.get_cache().enabled is False
    assert await access_version() is None
    await set_json("key", {"value": 1})
    assert await get_json("key") is None


def test_pilot_rejects_remote_plain_redis(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "pilot")
    monkeypatch.setenv("REDIS_URL", "redis://redis.example:6379/0")

    with pytest.raises(ValidationError):
        Settings()


def test_pilot_accepts_loopback_and_tls_redis(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "pilot")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    assert Settings().redis_url is not None

    monkeypatch.setenv("REDIS_URL", "rediss://user:secret@redis.example:6380/0")
    assert Settings().redis_url is not None

    monkeypatch.setenv("REDIS_URL", "")
    assert Settings().redis_url == ""


@pytest.mark.asyncio
async def test_version_and_json_round_trip(monkeypatch) -> None:
    fake = FakeCache()
    monkeypatch.setattr(cache_module, "_cache", fake)
    monkeypatch.setattr(cache_module.settings, "redis_cache_ttl_seconds", 45)

    assert await access_version() == 1
    assert await access_version() == 1
    assert await bump_access_version() == 2
    assert await access_version() == 2

    await set_json("access-key", {"allowed": True})
    assert await get_json("access-key") == {"allowed": True}
    assert fake.ttls["access-key"] == 45


@pytest.mark.asyncio
async def test_redis_failure_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(cache_module, "_cache", BrokenCache())

    assert await access_version() is None
    assert await get_json("access-key") is None
    assert await bump_access_version() is None
    await set_json("access-key", {"allowed": True})


def test_cache_key_contains_version() -> None:
    key = access_cache_key("permissions", "user:school", 7)
    assert key.endswith(":access:7:permissions:user:school")


def test_permissions_serialization_round_trip() -> None:
    group_id = uuid.uuid4()
    grant = PermissionGrant(
        code="journal.grades.read",
        effect="allow",
        depth=3,
        scope_type="school",
        group_id=group_id,
        group_code="school-teachers",
        group_name="Учителя школы",
    )
    access = EffectivePermissions(
        allowed={"journal.grades.read": True},
        grants={"journal.grades.read": grant},
        group_count=1,
    )

    restored = _permissions_from_cache(_permissions_to_cache(access))

    assert restored.allowed == access.allowed
    assert restored.group_count == 1
    assert restored.grants["journal.grades.read"] == grant


def test_service_states_serialization_round_trip() -> None:
    scope_id = uuid.uuid4()
    states = {
        "lms": ServiceState(
            code="lms",
            enabled=True,
            source="activation",
            depth=3,
            scope_type="school",
            scope_id=scope_id,
            config={"max_students": 500},
        )
    }

    restored = _service_states_from_cache(_service_states_to_cache(states))

    assert restored == states


@pytest.mark.asyncio
async def test_effective_permissions_uses_cache(monkeypatch) -> None:
    calls: list[uuid.UUID] = []

    async def fake_load_groups(_session, user):
        calls.append(user.id)
        return []

    monkeypatch.setattr(access_module, "load_user_groups", fake_load_groups)
    monkeypatch.setattr(cache_module, "_cache", FakeCache())
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role="student",
        school_id=uuid.uuid4(),
    )

    first = await effective_permissions(None, user)
    second = await effective_permissions(None, user)

    assert first.allowed == {}
    assert second.allowed == {}
    assert calls == [user.id]
