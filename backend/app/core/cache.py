"""Optional Redis cache for access decisions.

PostgreSQL remains the source of truth.  Redis is used only as a short-lived
cache in front of permission and service-activation resolution, so an outage
degrades latency but never blocks authentication or authorization.

Set ``REDIS_URL`` to enable the cache.  When it is empty the application uses a
no-op cache, which keeps local tests and the current pilot independent from
Redis.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

log = logging.getLogger("school-platform.cache")

# A short circuit breaker avoids a one-second Redis timeout on every request
# while the cache is down.  After the cooldown the next request tries again.
_FAILURE_COOLDOWN_SECONDS = 30.0
_failure_until = 0.0
_warned = False


class CacheClient(Protocol):
    enabled: bool

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int | None) -> None: ...

    async def incr(self, key: str) -> int: ...

    async def ping(self) -> bool: ...

    async def aclose(self) -> None: ...


class NullCache:
    enabled = False

    async def get(self, _key: str) -> str | None:
        return None

    async def set(self, _key: str, _value: str, _ttl: int | None) -> None:
        return None

    async def incr(self, _key: str) -> int:
        return 0

    async def ping(self) -> bool:
        return False

    async def aclose(self) -> None:
        return None


class RedisCache:
    enabled = True

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int | None) -> None:
        await self._client.set(key, value, ex=ttl)

    async def incr(self, key: str) -> int:
        return int(await self._client.incr(key))

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    async def aclose(self) -> None:
        await self._client.aclose()


_cache: CacheClient | None = None


def _prefix() -> str:
    return settings.redis_key_prefix.strip() or "school-platform"


def _version_key() -> str:
    return f"{_prefix()}:access:version"


def _available() -> bool:
    return time.monotonic() >= _failure_until


def _mark_failure() -> None:
    global _failure_until, _warned
    _failure_until = time.monotonic() + _FAILURE_COOLDOWN_SECONDS
    if not _warned:
        log.warning("Redis cache unavailable; falling back to PostgreSQL")
        _warned = True


def _mark_success() -> None:
    global _failure_until, _warned
    _failure_until = 0.0
    _warned = False


def get_cache() -> CacheClient:
    """Return the process-wide cache client, creating it lazily."""
    global _cache
    if _cache is None:
        if not settings.redis_url:
            _cache = NullCache()
        else:
            client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=settings.redis_socket_timeout_seconds,
                socket_timeout=settings.redis_socket_timeout_seconds,
                health_check_interval=30,
            )
            _cache = RedisCache(client)
    return _cache


async def close_cache() -> None:
    global _cache
    if _cache is not None:
        try:
            await _cache.aclose()
        except Exception:  # noqa: BLE001 - shutdown must not raise
            log.debug("Redis cache close failed", exc_info=True)
        _cache = None
    _mark_success()


def reset_cache_for_tests() -> None:
    """Reset module state in unit tests without touching a real Redis."""
    global _cache
    _cache = None
    _mark_success()


def access_cache_key(kind: str, subject: str, version: int) -> str:
    return f"{_prefix()}:access:{version}:{kind}:{subject}"


async def access_version() -> int | None:
    """Return the cache generation, or ``None`` when the cache is disabled."""
    cache = get_cache()
    if not cache.enabled or not _available():
        return None
    try:
        raw = await cache.get(_version_key())
        if raw is None:
            await cache.set(_version_key(), "1", None)
            _mark_success()
            return 1
        version = int(raw)
        _mark_success()
        return version
    except (RedisError, OSError, ValueError):
        _mark_failure()
        return None


async def bump_access_version() -> int | None:
    """Invalidate every access cache entry after a permission change."""
    cache = get_cache()
    if not cache.enabled or not _available():
        return None
    try:
        version = await cache.incr(_version_key())
        _mark_success()
        return version
    except (RedisError, OSError):
        _mark_failure()
        return None


async def get_json(key: str) -> Any | None:
    cache = get_cache()
    if not cache.enabled or not _available():
        return None
    try:
        raw = await cache.get(key)
        _mark_success()
        if raw is None:
            return None
        return json.loads(raw)
    except (RedisError, OSError, ValueError, TypeError):
        _mark_failure()
        return None


async def set_json(key: str, value: Any, ttl: int | None = None) -> None:
    cache = get_cache()
    if not cache.enabled or not _available():
        return
    try:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        ttl_seconds = ttl if ttl is not None else settings.redis_cache_ttl_seconds
        await cache.set(key, payload, max(1, int(ttl_seconds)))
        _mark_success()
    except (RedisError, OSError, TypeError, ValueError):
        _mark_failure()


async def cache_ping() -> bool:
    cache = get_cache()
    if not cache.enabled:
        return False
    try:
        ok = await cache.ping()
        if ok:
            _mark_success()
        else:
            _mark_failure()
        return ok
    except (RedisError, OSError):
        _mark_failure()
        return False
