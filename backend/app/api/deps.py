"""API dependencies: authentication, roles and tenant scope."""
from __future__ import annotations

import uuid
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_access_token
from app.db.session import get_session
from app.models.iam import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (TokenError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: str) -> Callable:
    """Return a dependency that allows only the listed roles."""
    allowed = frozenset(allowed_roles)

    async def checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return checker


AdminUser = Annotated[User, Depends(require_roles("superadmin", "admin"))]
AnyStaffUser = Annotated[
    User,
    Depends(
        require_roles(
            "superadmin",
            "admin",
            "methodologist",
            "teacher",
            "psychologist",
            "secretary",
        )
    ),
]


def ensure_school_access(user: User, school_id: uuid.UUID | None) -> uuid.UUID:
    """Validate and return the tenant a request may operate on."""
    if user.role == "superadmin":
        if school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required for a superadmin request",
            )
        return school_id

    if user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not attached to a school",
        )
    if school_id is not None and school_id != user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access is forbidden",
        )
    return user.school_id


async def tenant_school_id(
    current_user: CurrentUser,
    school_id: Annotated[
        uuid.UUID | None,
        Query(description="Required for superadmin; ignored for school users"),
    ] = None,
) -> uuid.UUID:
    return ensure_school_access(current_user, school_id)


TenantSchoolId = Annotated[uuid.UUID, Depends(tenant_school_id)]
