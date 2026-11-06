"""Runtime platform settings stored in ``system.settings``.

Only non-secret operational parameters live here.  Connection credentials
(``REDIS_URL``) stay in the deployment secret store; the admin console only
sees whether an endpoint is configured and whether it uses TLS.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.system import Setting

log = logging.getLogger("school-platform.settings")

CACHE_SETTINGS_KEY = "cache.runtime"
_CACHE_SETTINGS_REFRESH_SECONDS = 15.0
_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.-]{0,63}$")

_snapshot: "CacheRuntimeSettings | None" = None
_loaded_at = 0.0


def _normalise_prefix(value: Any, fallback: str) -> str:
    if isinstance(value, str):
        candidate = value.strip()
        if _PREFIX_RE.fullmatch(candidate):
            return candidate
    return fallback


def _number_in_range(
    value: Any,
    *,
    minimum: float,
    maximum: float,
    fallback: float,
    integer: bool = False,
) -> int | float:
    if isinstance(value, bool):
        return fallback
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if not minimum <= parsed <= maximum:
        return fallback
    return int(parsed) if integer else parsed


@dataclass(frozen=True, slots=True)
class CacheRuntimeSettings:
    """Effective, validated cache settings for the current process."""

    enabled: bool
    ttl_seconds: int
    key_prefix: str
    socket_timeout_seconds: float
    failure_cooldown_seconds: float
    source: str = "env"
    updated_at: datetime | None = None
    updated_by: str | None = None

    @property
    def endpoint_configured(self) -> bool:
        return bool(settings.redis_url)

    @property
    def tls_enabled(self) -> bool:
        return bool(
            settings.redis_url and settings.redis_url.startswith("rediss://")
        )

    @property
    def effective_enabled(self) -> bool:
        return self.enabled and self.endpoint_configured

    @property
    def mode(self) -> str:
        if not self.effective_enabled:
            return "disabled"
        return "managed-redis-tls" if self.tls_enabled else "redis"

    @property
    def fail_open(self) -> bool:
        # Availability is intentional: PostgreSQL remains the source of truth.
        return True

    @property
    def invalidation(self) -> str:
        return "version"


def _env_defaults(*, enabled: bool | None = None) -> CacheRuntimeSettings:
    configured = bool(settings.redis_url)
    return CacheRuntimeSettings(
        enabled=configured if enabled is None else enabled,
        ttl_seconds=max(1, int(settings.redis_cache_ttl_seconds)),
        key_prefix=_normalise_prefix(settings.redis_key_prefix, "school-platform"),
        socket_timeout_seconds=max(
            0.1, float(settings.redis_socket_timeout_seconds)
        ),
        failure_cooldown_seconds=max(
            1.0, float(settings.redis_failure_cooldown_seconds)
        ),
        source="env",
    )


def _coerce(
    raw: Any,
    *,
    updated_at: datetime | None = None,
    updated_by: str | None = None,
) -> CacheRuntimeSettings:
    """Validate a JSONB dictionary, falling back per field on bad input."""
    fallback = _env_defaults()
    if not isinstance(raw, dict):
        return CacheRuntimeSettings(
            enabled=fallback.enabled,
            ttl_seconds=fallback.ttl_seconds,
            key_prefix=fallback.key_prefix,
            socket_timeout_seconds=fallback.socket_timeout_seconds,
            failure_cooldown_seconds=fallback.failure_cooldown_seconds,
            source="database",
            updated_at=updated_at,
            updated_by=updated_by,
        )

    enabled = raw.get("enabled", fallback.enabled)
    if not isinstance(enabled, bool):
        enabled = fallback.enabled
    ttl_seconds = int(
        _number_in_range(
            raw.get("ttl_seconds"),
            minimum=5,
            maximum=3600,
            fallback=fallback.ttl_seconds,
            integer=True,
        )
    )
    socket_timeout_seconds = float(
        _number_in_range(
            raw.get("socket_timeout_seconds"),
            minimum=0.1,
            maximum=10.0,
            fallback=fallback.socket_timeout_seconds,
        )
    )
    failure_cooldown_seconds = float(
        _number_in_range(
            raw.get("failure_cooldown_seconds"),
            minimum=1.0,
            maximum=300.0,
            fallback=fallback.failure_cooldown_seconds,
        )
    )
    return CacheRuntimeSettings(
        enabled=enabled,
        ttl_seconds=ttl_seconds,
        key_prefix=_normalise_prefix(
            raw.get("key_prefix"), fallback.key_prefix
        ),
        socket_timeout_seconds=socket_timeout_seconds,
        failure_cooldown_seconds=failure_cooldown_seconds,
        source="database",
        updated_at=updated_at,
        updated_by=updated_by,
    )


def current_cache_settings() -> CacheRuntimeSettings:
    """Return the last loaded snapshot without touching the database."""
    if _snapshot is None:
        return _env_defaults()
    return _snapshot


async def get_cache_runtime(
    *,
    force: bool = False,
    include_disabled: bool = False,
) -> CacheRuntimeSettings:
    """Load the runtime setting from PostgreSQL when the snapshot is stale.

    Cache operations call this without ``include_disabled`` so a deployment
    without ``REDIS_URL`` never opens a needless database session.  The admin
    console uses ``include_disabled=True`` to inspect saved values before an
    endpoint is configured.
    """
    global _snapshot, _loaded_at

    if not settings.redis_url and not include_disabled:
        return _env_defaults(enabled=False)

    now = time.monotonic()
    if (
        not force
        and _snapshot is not None
        and now - _loaded_at < _CACHE_SETTINGS_REFRESH_SECONDS
    ):
        return _snapshot

    try:
        async with AsyncSessionLocal() as session:
            row = await session.get(Setting, CACHE_SETTINGS_KEY)
    except Exception as exc:  # noqa: BLE001 - settings must not break requests
        log.warning(
            "Runtime settings are unavailable; using environment defaults: %s",
            type(exc).__name__,
        )
        if _snapshot is None:
            _snapshot = _env_defaults()
        _loaded_at = now
        return _snapshot

    if row is None:
        _snapshot = _env_defaults()
    else:
        _snapshot = _coerce(
            row.value,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )
    _loaded_at = now
    return _snapshot


async def save_cache_settings(
    session: AsyncSession,
    updates: dict[str, Any],
    user_id: uuid.UUID,
) -> Setting:
    """Merge validated updates into ``system.settings`` without committing."""
    row = await session.get(Setting, CACHE_SETTINGS_KEY)
    current = (
        dict(row.value)
        if row is not None and isinstance(row.value, dict)
        else {}
    )
    merged = {**current, **updates}
    if row is None:
        row = Setting(
            key=CACHE_SETTINGS_KEY,
            value=merged,
            description="Runtime access-cache settings (non-secret).",
            updated_by=str(user_id),
        )
        session.add(row)
    else:
        row.value = merged
        row.updated_by = str(user_id)
    return row


def reset_cache_runtime_for_tests() -> None:
    """Reset the process snapshot in unit tests."""
    global _snapshot, _loaded_at
    _snapshot = None
    _loaded_at = 0.0
