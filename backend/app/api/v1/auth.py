"""Authentication API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import Message
from app.services.auth import (
    AuthError,
    authenticate,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post(
    "/login",
    response_model=TokenPair,
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

    raw_refresh, refresh_model = await issue_refresh_token(
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
