"""Operational settings for the republican administrator.

Only non-secret parameters are exposed.  ``REDIS_URL`` remains in the
deployment secret store; the UI receives a boolean "configured" flag and the
TLS mode instead of the credential itself.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_permission, require_roles
from app.core.cache import (
    apply_cache_runtime_settings,
    cache_ping,
)
from app.core.config import settings
from app.models.iam import User
from app.schemas.platform_settings import (
    CacheSettingsOut,
    CacheSettingsUpdate,
    CacheTestOut,
)
from app.services.audit import add_audit_event
from app.services.platform_settings import (
    CACHE_SETTINGS_KEY,
    CacheRuntimeSettings,
    get_cache_runtime,
    save_cache_settings,
)

router = APIRouter(prefix="/admin/settings", tags=["admin"])

SETTINGS_READ = require_permission("system.settings.read")
SETTINGS_WRITE = require_permission("system.settings.write")
SUPERADMIN = require_roles("superadmin")


async def _probe(runtime: CacheRuntimeSettings) -> tuple[str, float | None]:
    if not runtime.effective_enabled:
        return "disabled", None
    started = time.perf_counter()
    ok = await cache_ping()
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return ("connected" if ok else "unavailable"), latency_ms


def _as_out(
    runtime: CacheRuntimeSettings,
    cache_status: str,
    latency_ms: float | None,
) -> CacheSettingsOut:
    return CacheSettingsOut(
        enabled=runtime.enabled,
        effective_enabled=runtime.effective_enabled,
        mode=runtime.mode,
        endpoint_configured=runtime.endpoint_configured,
        tls_enabled=runtime.tls_enabled,
        ttl_seconds=runtime.ttl_seconds,
        key_prefix=runtime.key_prefix,
        socket_timeout_seconds=runtime.socket_timeout_seconds,
        failure_cooldown_seconds=runtime.failure_cooldown_seconds,
        fail_open=runtime.fail_open,
        invalidation=runtime.invalidation,
        source=runtime.source,
        status=cache_status,
        latency_ms=latency_ms,
        updated_at=runtime.updated_at,
        updated_by=runtime.updated_by,
        requires_restart=False,
    )


@router.get(
    "/cache",
    response_model=CacheSettingsOut,
    summary="Настройки кеша доступа",
)
async def get_cache_settings(
    _current_user: User = Depends(SUPERADMIN),
    _permission: User = Depends(SETTINGS_READ),
) -> CacheSettingsOut:
    """Return effective cache settings and a live connection probe."""
    runtime = await get_cache_runtime(force=True, include_disabled=True)
    cache_status, latency_ms = await _probe(runtime)
    return _as_out(runtime, cache_status, latency_ms)


@router.patch(
    "/cache",
    response_model=CacheSettingsOut,
    summary="Изменить настройки кеша доступа",
)
async def update_cache_settings(
    payload: CacheSettingsUpdate,
    session: SessionDep,
    current_user: User = Depends(SUPERADMIN),
    _permission: User = Depends(SETTINGS_WRITE),
) -> CacheSettingsOut:
    """Persist non-secret cache settings and invalidate the local snapshot."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one setting must be provided",
        )
    if updates.get("enabled") is True and not settings.redis_url:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "REDIS_URL is not configured. Add it to the deployment secret "
                "store before enabling the cache."
            ),
        )

    await save_cache_settings(session, updates, current_user.id)
    add_audit_event(
        session,
        action="platform.cache.settings.update",
        entity_type="platform.cache",
        entity_id=CACHE_SETTINGS_KEY,
        user_id=current_user.id,
        details={
            "updated": sorted(updates),
            "values": {key: updates[key] for key in sorted(updates)},
        },
    )
    await session.commit()

    await apply_cache_runtime_settings()
    runtime = await get_cache_runtime(force=True, include_disabled=True)
    cache_status, latency_ms = await _probe(runtime)
    return _as_out(runtime, cache_status, latency_ms)


@router.post(
    "/cache/test",
    response_model=CacheTestOut,
    summary="Проверить подключение к кешу",
)
async def test_cache_connection(
    _current_user: User = Depends(SUPERADMIN),
    _permission: User = Depends(SETTINGS_WRITE),
) -> CacheTestOut:
    """Probe Redis without changing settings or exposing the endpoint."""
    runtime = await get_cache_runtime(force=True, include_disabled=True)
    cache_status, latency_ms = await _probe(runtime)
    if cache_status == "disabled":
        message = "Кеш отключён или REDIS_URL не настроен"
    elif cache_status == "connected":
        message = "Подключение к Redis установлено"
    else:
        message = "Redis недоступен; запросы продолжают работать с PostgreSQL"
    return CacheTestOut(
        ok=cache_status == "connected",
        status=cache_status,
        mode=runtime.mode,
        latency_ms=latency_ms,
        message=message,
    )
