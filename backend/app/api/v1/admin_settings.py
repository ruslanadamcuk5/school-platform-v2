"""Operational settings for the republican administrator.

Only non-secret parameters are exposed.  ``REDIS_URL`` remains in the
deployment secret store; the UI receives a boolean "configured" flag and the
TLS mode instead of the credential itself.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import SessionDep, require_permission, require_roles
from app.core.cache import (
    apply_cache_runtime_settings,
    cache_ping,
)
from app.core.config import settings
from app.models.audit import AuditEvent
from app.models.iam import User
from app.schemas.platform_settings import (
    CacheSettingsHistory,
    CacheSettingsHistoryItem,
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

CACHE_AUDIT_ACTION = "platform.cache.settings.update"
CACHE_ENTITY_TYPE = "platform.cache"

router = APIRouter(prefix="/admin/settings", tags=["admin"])

SETTINGS_READ = require_permission("system.settings.read")
SETTINGS_WRITE = require_permission("system.settings.write")
SUPERADMIN = require_roles("superadmin")


def _dangerous_changes(
    runtime: CacheRuntimeSettings,
    updates: dict[str, object],
) -> list[str]:
    """Return a human-readable list of availability/invalidation risks."""
    changes: list[str] = []
    if updates.get("enabled") is False and runtime.enabled:
        changes.append("отключение кеша")
    if "key_prefix" in updates and updates["key_prefix"] != runtime.key_prefix:
        changes.append("смена префикса ключей и полная инвалидация")
    return changes


def _values_for(
    runtime: CacheRuntimeSettings,
    keys: list[str],
) -> dict[str, object]:
    return {key: getattr(runtime, key) for key in keys}


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
    updates = payload.model_dump(
        exclude_none=True,
        exclude={"confirm", "reason"},
    )
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

    runtime_before = await get_cache_runtime(
        force=True,
        include_disabled=True,
    )
    dangerous = _dangerous_changes(runtime_before, updates)
    if dangerous and not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=(
                "Confirmation required: "
                + "; ".join(dangerous)
                + ". Repeat the request with confirm=true."
            ),
        )

    reason = (payload.reason or "").strip() or None
    if dangerous and reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reason is required for a dangerous cache change",
        )

    await save_cache_settings(session, updates, current_user.id)
    add_audit_event(
        session,
        action=CACHE_AUDIT_ACTION,
        entity_type=CACHE_ENTITY_TYPE,
        entity_id=CACHE_SETTINGS_KEY,
        user_id=current_user.id,
        details={
            "updated": sorted(updates),
            "before": _values_for(runtime_before, sorted(updates)),
            "after": {key: updates[key] for key in sorted(updates)},
            "reason": reason,
            "confirmed_dangerous": bool(dangerous),
        },
    )
    await session.commit()

    await apply_cache_runtime_settings()
    runtime = await get_cache_runtime(force=True, include_disabled=True)
    cache_status, latency_ms = await _probe(runtime)
    return _as_out(runtime, cache_status, latency_ms)


@router.get(
    "/cache/history",
    response_model=CacheSettingsHistory,
    summary="История изменений настроек кеша",
)
async def cache_settings_history(
    session: SessionDep,
    _current_user: User = Depends(SUPERADMIN),
    _permission: User = Depends(SETTINGS_READ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CacheSettingsHistory:
    """Return the immutable audit trail for non-secret cache settings."""
    rows = (
        await session.execute(
            select(AuditEvent, User.login)
            .outerjoin(User, AuditEvent.user_id == User.id)
            .where(
                AuditEvent.action == CACHE_AUDIT_ACTION,
                AuditEvent.entity_type == CACHE_ENTITY_TYPE,
                AuditEvent.entity_id == CACHE_SETTINGS_KEY,
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return CacheSettingsHistory(
        items=[
            CacheSettingsHistoryItem(
                id=event.id,
                created_at=event.created_at,
                user_id=event.user_id,
                user_login=user_login,
                action=event.action,
                details=event.details or {},
            )
            for event, user_login in rows
        ],
        limit=limit,
        offset=offset,
    )


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
