"""Group-based access management API.

Permissions are never assigned to users directly.  An administrator creates a
group at a scope (class, school, city, region or country), attaches
permissions to the group and moves users in or out of it.  The access
resolver in :mod:`app.services.access` combines group inheritance with the
organisational hierarchy.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import SessionDep, ensure_scope_access, require_permission
from app.core.scopes import COUNTRY_SCOPE_ID, SCOPE_DEPTH
from app.models.iam import (
    GroupMembership,
    GroupPermission,
    Permission,
    User,
    UserGroup,
)
from app.models.org import ClassMembership
from app.schemas.groups import (
    GroupCreate,
    GroupDetailOut,
    GroupListOut,
    GroupMemberOut,
    GroupMembersAdd,
    GroupOut,
    GroupPermissionOut,
    GroupPermissionSet,
    GroupStatusOut,
    GroupUpdate,
    PermissionListOut,
    PermissionOut,
)
from app.services.access import user_scope_keys

router = APIRouter(prefix="/groups", tags=["iam"])

GroupsRead = Annotated[User, Depends(require_permission("iam.groups.read"))]
GroupsWrite = Annotated[User, Depends(require_permission("iam.groups.write"))]
PermissionsRead = Annotated[
    User, Depends(require_permission("iam.permissions.read"))
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _group_out(group: UserGroup) -> GroupOut:
    return GroupOut(
        id=group.id,
        code=group.code,
        name=group.name,
        description=group.description,
        category=group.category,
        scope_type=group.scope_type,
        scope_id=group.scope_id,
        depth=group.depth,
        parent_id=group.parent_id,
        is_system=group.is_system,
        is_active=group.is_active,
        members_count=len(group.memberships) if group.memberships is not None else 0,
        permissions_count=(
            len(group.permission_links)
            if group.permission_links is not None
            else 0
        ),
        created_at=group.created_at,
    )


def _group_detail(group: UserGroup) -> GroupDetailOut:
    base = _group_out(group)
    members = [
        GroupMemberOut(
            user_id=membership.user_id,
            login=membership.user.login,
            full_name=membership.user.full_name,
            role=membership.user.role,
            assigned_at=membership.assigned_at,
            expires_at=membership.expires_at,
            is_primary=membership.is_primary,
        )
        for membership in group.memberships
        if membership.user is not None
    ]
    permissions = [
        GroupPermissionOut(
            permission_code=link.permission.code,
            permission_name=link.permission.name,
            effect=link.effect,
            granted_at=link.granted_at,
            expires_at=link.expires_at,
        )
        for link in group.permission_links
        if link.permission is not None
    ]
    children = [_group_out(child) for child in group.children]
    return GroupDetailOut(
        **base.model_dump(),
        members=sorted(members, key=lambda item: item.full_name),
        permissions=sorted(permissions, key=lambda item: item.permission_code),
        children=sorted(children, key=lambda item: item.name),
    )


def _options():
    return (
        selectinload(UserGroup.memberships).selectinload(GroupMembership.user),
        selectinload(UserGroup.permission_links).selectinload(
            GroupPermission.permission
        ),
        selectinload(UserGroup.children),
        selectinload(UserGroup.children).selectinload(UserGroup.memberships),
        selectinload(UserGroup.children).selectinload(UserGroup.permission_links),
    )


async def _load_group(session: AsyncSession, group_id: uuid.UUID) -> UserGroup:
    group = (
        await session.execute(
            select(UserGroup).options(*_options()).where(UserGroup.id == group_id)
        )
    ).scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def _assert_scope_visible(
    session: AsyncSession, current_user: User, group: UserGroup
) -> None:
    if current_user.role == "superadmin":
        return
    scopes = await user_scope_keys(session, current_user)
    if (group.scope_type, group.scope_id) not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group is outside the user's organisational scope",
        )


def _resolve_scope(payload: GroupCreate) -> tuple[str, uuid.UUID]:
    if payload.scope_type == "country":
        return payload.scope_type, COUNTRY_SCOPE_ID
    if payload.scope_id is None:
        raise HTTPException(
            status_code=422,
            detail="scope_id is required for a non-country group",
        )
    return payload.scope_type, payload.scope_id


# -------------------------------------------------------------------- catalog
@router.get(
    "/permissions",
    response_model=PermissionListOut,
    summary="Каталог прав платформы",
)
async def list_permissions(
    current_user: PermissionsRead,
    session: SessionDep,
    service_code: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    conditions = []
    if service_code:
        conditions.append(Permission.service_code == service_code)
    if category:
        conditions.append(Permission.category == category)
    items = list(
        (
            await session.execute(
                select(Permission)
                .where(*conditions)
                .order_by(Permission.service_code, Permission.code)
            )
        )
        .scalars()
        .all()
    )
    return PermissionListOut(
        items=[PermissionOut.model_validate(item) for item in items],
        total=len(items),
    )


# ---------------------------------------------------------------------- list
@router.get("", response_model=GroupListOut, summary="Группы пользователей")
async def list_groups(
    current_user: GroupsRead,
    session: SessionDep,
    scope_type: str | None = Query(default=None),
    scope_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    if scope_type:
        if scope_type not in SCOPE_DEPTH:
            raise HTTPException(status_code=422, detail="Unknown scope type")
        conditions.append(UserGroup.scope_type == scope_type)
        if scope_type == "country":
            conditions.append(UserGroup.scope_id == COUNTRY_SCOPE_ID)
        elif scope_id is not None:
            conditions.append(UserGroup.scope_id == scope_id)
    if category:
        conditions.append(UserGroup.category == category)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                UserGroup.code.ilike(pattern),
                UserGroup.name.ilike(pattern),
            )
        )
    if not include_inactive:
        conditions.append(UserGroup.is_active.is_(True))

    if current_user.role != "superadmin":
        scopes = await user_scope_keys(session, current_user)
        conditions.append(
            tuple_(UserGroup.scope_type, UserGroup.scope_id).in_(scopes)
        )

    total = (
        await session.execute(
            select(func.count()).select_from(UserGroup).where(*conditions)
        )
    ).scalar_one()
    groups = list(
        (
            await session.execute(
                select(UserGroup)
                .options(*_options())
                .where(*conditions)
                .order_by(UserGroup.scope_type, UserGroup.category, UserGroup.name)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .unique()
        .all()
    )
    return GroupListOut(items=[_group_out(group) for group in groups], total=total)


@router.get(
    "/{group_id}",
    response_model=GroupDetailOut,
    summary="Карточка группы",
)
async def get_group(
    group_id: uuid.UUID,
    current_user: GroupsRead,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await _assert_scope_visible(session, current_user, group)
    return _group_detail(group)


# -------------------------------------------------------------------- create
@router.post(
    "",
    response_model=GroupDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать группу",
)
async def create_group(
    payload: GroupCreate,
    current_user: GroupsWrite,
    session: SessionDep,
):
    scope_type, scope_id = _resolve_scope(payload)
    await ensure_scope_access(session, current_user, scope_type, scope_id)

    parent = None
    if payload.parent_id is not None:
        parent = await session.get(UserGroup, payload.parent_id)
        if parent is None or not parent.is_active:
            raise HTTPException(status_code=404, detail="Parent group not found")
        if SCOPE_DEPTH[parent.scope_type] >= SCOPE_DEPTH[scope_type]:
            raise HTTPException(
                status_code=422,
                detail="Parent group must be at a higher scope level",
            )

    group = UserGroup(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        scope_type=scope_type,
        scope_id=scope_id,
        depth=SCOPE_DEPTH[scope_type],
        parent_id=parent.id if parent else None,
        is_system=payload.is_system,
        is_active=True,
        meta=payload.meta,
    )
    session.add(group)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A group with this code already exists in the scope",
        ) from exc
    await session.commit()
    return _group_detail(await _load_group(session, group.id))


# -------------------------------------------------------------------- update
@router.patch(
    "/{group_id}",
    response_model=GroupDetailOut,
    summary="Изменить группу",
)
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)
    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates and updates["parent_id"] is not None:
        if updates["parent_id"] == group.id:
            raise HTTPException(status_code=422, detail="A group cannot be its own parent")
        parent = await session.get(UserGroup, updates["parent_id"])
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent group not found")
        if SCOPE_DEPTH[parent.scope_type] >= group.depth:
            raise HTTPException(
                status_code=422,
                detail="Parent group must be at a higher scope level",
            )
    for field in ("name", "description", "category", "parent_id", "is_active", "meta"):
        if field in updates:
            setattr(group, field, updates[field])
    await session.commit()
    return _group_detail(await _load_group(session, group.id))


@router.delete(
    "/{group_id}",
    response_model=GroupStatusOut,
    summary="Отключить группу",
)
async def deactivate_group(
    group_id: uuid.UUID,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)
    if group.is_system:
        raise HTTPException(status_code=409, detail="System groups cannot be disabled")
    group.is_active = False
    await session.commit()
    return GroupStatusOut(message="Group disabled")


# ------------------------------------------------------------------ members
@router.post(
    "/{group_id}/members",
    response_model=GroupDetailOut,
    summary="Добавить пользователей в группу",
)
async def add_members(
    group_id: uuid.UUID,
    payload: GroupMembersAdd,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)

    users = list(
        (
            await session.execute(
                select(User).where(
                    User.id.in_(payload.user_ids), User.deleted_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    found = {user.id for user in users}
    missing = set(payload.user_ids) - found
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Users not found: {', '.join(str(item) for item in missing)}",
        )

    if group.scope_type == "school":
        wrong = [user for user in users if user.school_id != group.scope_id]
        if wrong:
            raise HTTPException(
                status_code=422,
                detail="All users must belong to the school of the group",
            )
    if group.scope_type == "class":
        rows = (
            await session.execute(
                select(ClassMembership.user_id).where(
                    ClassMembership.class_id == group.scope_id,
                    ClassMembership.user_id.in_(payload.user_ids),
                    ClassMembership.left_at.is_(None),
                )
            )
        ).scalars().all()
        if len(set(rows)) != len(set(payload.user_ids)):
            raise HTTPException(
                status_code=422,
                detail="All users must be active members of the class",
            )

    existing = (
        await session.execute(
            select(GroupMembership.user_id).where(
                GroupMembership.group_id == group.id,
                GroupMembership.user_id.in_(payload.user_ids),
            )
        )
    ).scalars().all()
    existing_set = set(existing)
    for user in users:
        if user.id in existing_set:
            continue
        session.add(
            GroupMembership(
                id=uuid.uuid4(),
                group_id=group.id,
                user_id=user.id,
                assigned_by=current_user.id,
                assigned_at=_now(),
                expires_at=payload.expires_at,
                is_primary=payload.is_primary,
            )
        )
    await session.commit()
    return _group_detail(await _load_group(session, group.id))


@router.delete(
    "/{group_id}/members/{user_id}",
    response_model=GroupStatusOut,
    summary="Исключить пользователя из группы",
)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)
    membership = (
        await session.execute(
            select(GroupMembership).where(
                GroupMembership.group_id == group.id,
                GroupMembership.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    await session.delete(membership)
    await session.commit()
    return GroupStatusOut(message="User removed from the group")


# -------------------------------------------------------------- permissions
@router.put(
    "/{group_id}/permissions/{permission_code}",
    response_model=GroupPermissionOut,
    summary="Назначить право группе",
)
async def set_group_permission(
    group_id: uuid.UUID,
    permission_code: str,
    payload: GroupPermissionSet,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)

    permission = (
        await session.execute(
            select(Permission).where(Permission.code == permission_code)
        )
    ).scalar_one_or_none()
    if permission is None:
        raise HTTPException(status_code=404, detail="Permission not found")

    link = (
        await session.execute(
            select(GroupPermission).where(
                GroupPermission.group_id == group.id,
                GroupPermission.permission_id == permission.id,
            )
        )
    ).scalar_one_or_none()
    granted_at = _now()
    if link is None:
        link = GroupPermission(
            id=uuid.uuid4(),
            group_id=group.id,
            permission_id=permission.id,
            effect=payload.effect,
            granted_by=current_user.id,
            granted_at=granted_at,
            expires_at=payload.expires_at,
        )
        session.add(link)
    else:
        link.effect = payload.effect
        link.expires_at = payload.expires_at
        link.granted_by = current_user.id
        link.granted_at = granted_at
    await session.commit()
    return GroupPermissionOut(
        permission_code=permission.code,
        permission_name=permission.name,
        effect=payload.effect,
        granted_at=granted_at,
        expires_at=payload.expires_at,
    )


@router.delete(
    "/{group_id}/permissions/{permission_code}",
    response_model=GroupStatusOut,
    summary="Снять право с группы",
)
async def remove_group_permission(
    group_id: uuid.UUID,
    permission_code: str,
    current_user: GroupsWrite,
    session: SessionDep,
):
    group = await _load_group(session, group_id)
    await ensure_scope_access(session, current_user, group.scope_type, group.scope_id)
    link = (
        await session.execute(
            select(GroupPermission)
            .join(Permission, Permission.id == GroupPermission.permission_id)
            .where(
                GroupPermission.group_id == group.id,
                Permission.code == permission_code,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Permission assignment not found")
    await session.delete(link)
    await session.commit()
    return GroupStatusOut(message="Permission removed")
