"""Authentication API."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_mfa_token,
    decode_mfa_token,
)
from app.models.iam import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MfaChallenge,
    MfaEnrollStart,
    MfaEnrollmentComplete,
    MfaStatus,
    MfaTokenRequest,
    MfaVerifyRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import Message
from app.services.audit import add_audit_event
from app.services.auth import (
    AuthError,
    authenticate,
    issue_refresh_token,
    record_login_success,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.mfa import (
    MFA_PURPOSE_ENROLL,
    MFA_PURPOSE_VERIFY,
    MfaError,
    MfaLockedError,
    complete_enrollment,
    recovery_codes_remaining,
    start_enrollment,
    verify_login_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def _load_mfa_user(
    session: SessionDep,
    *,
    token: str,
    purpose: str,
) -> User:
    try:
        payload = decode_mfa_token(token, purpose=purpose)
        user_id = uuid.UUID(str(payload["sub"]))
    except (TokenError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = await session.get(User, user_id, with_for_update=True)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post(
    "/login",
    response_model=TokenPair | MfaChallenge,
    summary="Вход по логину и паролю",
)
async def login(payload: LoginRequest, request: Request, session: SessionDep):
    user = await authenticate(
        session,
        login=payload.login,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.mfa_enabled:
        mfa_token, _expires_at = create_mfa_token(
            user_id=user.id,
            purpose=MFA_PURPOSE_VERIFY,
            ttl_seconds=settings.mfa_challenge_ttl_seconds,
        )
        add_audit_event(
            session,
            action="login_mfa_required",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
            details={"login": user.login},
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        await session.commit()
        return MfaChallenge(
            status="mfa_required",
            mfa_token=mfa_token,
            expires_in=settings.mfa_challenge_ttl_seconds,
            user=UserOut.model_validate(user),
        )

    if user.role == "superadmin":
        mfa_token, _expires_at = create_mfa_token(
            user_id=user.id,
            purpose=MFA_PURPOSE_ENROLL,
            ttl_seconds=settings.mfa_enrollment_ttl_seconds,
        )
        add_audit_event(
            session,
            action="login_mfa_enrollment_required",
            entity_type="user",
            entity_id=user.id,
            school_id=user.school_id,
            user_id=user.id,
            details={"login": user.login},
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        await session.commit()
        return MfaChallenge(
            status="mfa_enrollment_required",
            mfa_token=mfa_token,
            expires_in=settings.mfa_enrollment_ttl_seconds,
            user=UserOut.model_validate(user),
        )

    record_login_success(
        session,
        user=user,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    raw_refresh, _refresh_model = await issue_refresh_token(
        session,
        user=user,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await session.commit()
    access_token, _expires_at = create_access_token(
        user_id=user.id,
        role=user.role,
        school_id=user.school_id,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Обновление access-токена",
)
async def refresh(payload: RefreshRequest, request: Request, session: SessionDep):
    try:
        user, raw_refresh, _model = await rotate_refresh_token(
            session,
            raw_token=payload.refresh_token,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        await session.commit()
    except AuthError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    access_token, _expires_at = create_access_token(
        user_id=user.id,
        role=user.role,
        school_id=user.school_id,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/mfa/enroll/start",
    response_model=MfaEnrollStart,
    summary="Начать настройку MFA",
)
async def mfa_enroll_start(
    payload: MfaTokenRequest,
    session: SessionDep,
) -> MfaEnrollStart:
    user = await _load_mfa_user(
        session,
        token=payload.mfa_token,
        purpose=MFA_PURPOSE_ENROLL,
    )
    try:
        secret, otpauth_uri = await start_enrollment(session, user=user)
    except MfaLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except MfaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    await session.commit()
    return MfaEnrollStart(
        secret=secret,
        otpauth_uri=otpauth_uri,
        expires_in=settings.mfa_enrollment_ttl_seconds,
    )


@router.post(
    "/mfa/enroll/verify",
    response_model=MfaEnrollmentComplete,
    summary="Завершить настройку MFA",
)
async def mfa_enroll_verify(
    payload: MfaVerifyRequest,
    request: Request,
    session: SessionDep,
) -> MfaEnrollmentComplete:
    user = await _load_mfa_user(
        session,
        token=payload.mfa_token,
        purpose=MFA_PURPOSE_ENROLL,
    )
    try:
        recovery_codes = await complete_enrollment(
            session,
            user=user,
            code=payload.code,
        )
    except MfaLockedError as exc:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except MfaError as exc:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    record_login_success(
        session,
        user=user,
        mfa_used=True,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    raw_refresh, _refresh_model = await issue_refresh_token(
        session,
        user=user,
        mfa_verified=True,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await session.commit()
    access_token, _expires_at = create_access_token(
        user_id=user.id,
        role=user.role,
        school_id=user.school_id,
    )
    return MfaEnrollmentComplete(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
        user=UserOut.model_validate(user),
        recovery_codes=recovery_codes,
    )


@router.post(
    "/mfa/verify",
    response_model=TokenPair,
    summary="Подтвердить вход кодом MFA",
)
async def mfa_verify(
    payload: MfaVerifyRequest,
    request: Request,
    session: SessionDep,
) -> TokenPair:
    user = await _load_mfa_user(
        session,
        token=payload.mfa_token,
        purpose=MFA_PURPOSE_VERIFY,
    )
    try:
        await verify_login_code(
            session,
            user=user,
            code=payload.code,
        )
    except MfaLockedError as exc:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except MfaError as exc:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    record_login_success(
        session,
        user=user,
        mfa_used=True,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    raw_refresh, _refresh_model = await issue_refresh_token(
        session,
        user=user,
        mfa_verified=True,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    await session.commit()
    access_token, _expires_at = create_access_token(
        user_id=user.id,
        role=user.role,
        school_id=user.school_id,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
        user=UserOut.model_validate(user),
    )


@router.get("/mfa/status", response_model=MfaStatus, summary="Статус MFA")
async def mfa_status(
    current_user: CurrentUser,
    session: SessionDep,
) -> MfaStatus:
    remaining = await recovery_codes_remaining(session, user_id=current_user.id)
    return MfaStatus(
        enabled=current_user.mfa_enabled,
        recovery_codes_remaining=remaining,
        enrolled_at=current_user.mfa_enrolled_at,
    )


@router.post("/logout", response_model=Message, summary="Выход из системы")
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
    if payload.refresh_token:
        await revoke_refresh_token(
            session,
            raw_token=payload.refresh_token,
            user_id=current_user.id,
        )
        await session.commit()
    return Message(status="ok", detail="Session revoked")


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
async def me(current_user: CurrentUser):
    return current_user
