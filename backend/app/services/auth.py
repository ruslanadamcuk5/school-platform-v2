"""Authentication and refresh-session service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_refresh_token,
    new_refresh_token,
    refresh_expires_at,
    verify_password,
)
from app.models.iam import RefreshToken, User
from app.services.audit import add_audit_event


class AuthError(ValueError):
    """Authentication or refresh-token error."""


def _client_info(
    ip_address: str | None, user_agent: str | None
) -> dict[str, str | None]:
    return {
        "ip_address": ip_address[:64] if ip_address else None,
        "user_agent": user_agent[:512] if user_agent else None,
    }


async def authenticate(
    session: AsyncSession,
    *,
    login: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User | None:
    normalized = login.strip()
    user = (
        await session.execute(
            select(User).where(
                User.login == normalized,
                User.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        add_audit_event(
            session,
            action="login_failed",
            entity_type="user",
            entity_id=None,
            details={"login": normalized, "reason": "bad_credentials"},
            **_client_info(ip_address, user_agent),
        )
        await session.commit()
        return None

    if not user.is_active:
        add_audit_event(
            session,
            action="login_failed",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
            details={"login": normalized, "reason": "inactive"},
            **_client_info(ip_address, user_agent),
        )
        await session.commit()
        return None

    user.last_login_at = datetime.now(timezone.utc)
    add_audit_event(
        session,
        action="login_success",
        entity_type="user",
        entity_id=user.id,
        school_id=user.school_id,
        user_id=user.id,
        details={"login": user.login, "role": user.role},
        **_client_info(ip_address, user_agent),
    )
    return user


async def issue_refresh_token(
    session: AsyncSession,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, RefreshToken]:
    raw_token, token_hash = new_refresh_token()
    model = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=refresh_expires_at(),
        user_agent=user_agent[:512] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
    )
    session.add(model)
    return raw_token, model


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str, RefreshToken]:
    token_hash = hash_refresh_token(raw_token)
    token = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if token is None or not token.is_active:
        raise AuthError("Refresh token is invalid, expired or revoked")

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        token.revoked_at = datetime.now(timezone.utc)
        raise AuthError("User is not active")

    token.revoked_at = datetime.now(timezone.utc)
    raw_new, new_model = await issue_refresh_token(
        session,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    add_audit_event(
        session,
        action="token_refresh",
        entity_type="refresh_token",
        entity_id=new_model.id,
        school_id=user.school_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user, raw_new, new_model


async def revoke_refresh_token(
    session: AsyncSession,
    *,
    raw_token: str,
    user_id: uuid.UUID | None = None,
) -> bool:
    token_hash = hash_refresh_token(raw_token)
    token = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if token is None:
        return False
    if user_id is not None and token.user_id != user_id:
        return False
    if token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        add_audit_event(
            session,
            action="logout",
            entity_type="refresh_token",
            entity_id=token.id,
            user_id=token.user_id,
        )
    return True
