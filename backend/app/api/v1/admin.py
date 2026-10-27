"""Administration API: users, statistics and audit, scoped by school."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import AdminUser, SessionDep, ensure_school_access
from app.core.security import hash_password
from app.models.audit import AuditEvent
from app.models.iam import ROLE_VALUES, User
from app.models.org import SchoolClass
from app.schemas.auth import (
    AdminStats,
    AuditList,
    UserCreate,
    UserList,
    UserOut,
)
from app.services.audit import add_audit_event

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats, summary="Сводка по школе")
async def stats(
    current_user: AdminUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)

    users_total = (
        await session.execute(
            select(func.count()).select_from(User).where(
                User.school_id == tenant_id, User.deleted_at.is_(None)
            )
        )
    ).scalar_one()
    users_active = (
        await session.execute(
            select(func.count()).select_from(User).where(
                User.school_id == tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
    ).scalar_one()
    classes_total = (
        await session.execute(
            select(func.count()).select_from(SchoolClass).where(
                SchoolClass.school_id == tenant_id,
                SchoolClass.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    classes_active = (
        await session.execute(
            select(func.count()).select_from(SchoolClass).where(
                SchoolClass.school_id == tenant_id,
                SchoolClass.deleted_at.is_(None),
                SchoolClass.is_active.is_(True),
            )
        )
    ).scalar_one()
    role_rows = (
        await session.execute(
            select(User.role, func.count())
            .where(User.school_id == tenant_id, User.deleted_at.is_(None))
            .group_by(User.role)
        )
    ).all()

    return AdminStats(
        school_id=tenant_id,
        users_total=users_total,
        users_active=users_active,
        by_role={role: count for role, count in role_rows},
        classes_total=classes_total,
        classes_active=classes_active,
    )


@router.get("/users", response_model=UserList, summary="Пользователи школы")
async def list_users(
    current_user: AdminUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    tenant_id = ensure_school_access(current_user, school_id)
    conditions = [User.school_id == tenant_id, User.deleted_at.is_(None)]
    if role:
        if role not in ROLE_VALUES:
            raise HTTPException(status_code=422, detail="Unknown role")
        conditions.append(User.role == role)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.login.ilike(pattern),
                User.email.ilike(pattern),
                User.last_name.ilike(pattern),
                User.first_name.ilike(pattern),
            )
        )

    total = (
        await session.execute(
            select(func.count()).select_from(User).where(*conditions)
        )
    ).scalar_one()
    items = (
        await session.execute(
            select(User)
            .where(*conditions)
            .order_by(User.last_name, User.first_name, User.login)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return UserList(
        items=[UserOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создание пользователя школы",
)
async def create_user(
    payload: UserCreate,
    current_user: AdminUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)
    if payload.role not in ROLE_VALUES:
        raise HTTPException(status_code=422, detail="Unknown role")
    if payload.role == "superadmin" and current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can create superadmin",
        )

    existing = (
        await session.execute(select(User.id).where(User.login == payload.login))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login is already taken",
        )

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = User(
        school_id=tenant_id,
        login=payload.login.strip(),
        email=str(payload.email) if payload.email else None,
        password_hash=password_hash,
        role=payload.role,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        middle_name=payload.middle_name,
        phone=payload.phone,
        must_change_password=True,
    )
    session.add(user)
    await session.flush()
    add_audit_event(
        session,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        school_id=tenant_id,
        user_id=current_user.id,
        details={"login": user.login, "role": user.role},
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/audit", response_model=AuditList, summary="Журнал аудита")
async def audit_events(
    current_user: AdminUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    tenant_id = ensure_school_access(current_user, school_id)
    items = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.school_id == tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return AuditList(items=items, limit=limit, offset=offset)
