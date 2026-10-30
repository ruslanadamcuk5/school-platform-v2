"""Personal access endpoints used by every client to build navigation.

The web, Android and iOS clients call ``/me/services`` to render only the
functionality enabled for the user's scope, and ``/me/permissions`` to show
or hide individual actions.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.models.iam import GroupMembership, GroupPermission, UserGroup
from app.schemas.groups import (
    EffectivePermissionOut,
    GroupOut,
    MyPermissionsOut,
)
from app.schemas.services import EffectiveServiceOut, MyServicesOut
from app.services.access import (
    effective_permissions,
    load_user_groups,
    visible_services,
)

router = APIRouter(prefix="/me", tags=["iam"])


def _options():
    return (
        selectinload(UserGroup.memberships).selectinload(GroupMembership.user),
        selectinload(UserGroup.permission_links).selectinload(
            GroupPermission.permission
        ),
        selectinload(UserGroup.children),
    )


@router.get(
    "/permissions",
    response_model=MyPermissionsOut,
    summary="Действующие права пользователя",
)
async def my_permissions(current_user: CurrentUser, session: SessionDep):
    access = await effective_permissions(session, current_user)
    groups = await load_user_groups(session, current_user)

    details = [
        EffectivePermissionOut(
            code=code,
            allowed=allowed,
            effect=access.grants[code].effect,
            scope_type=access.grants[code].scope_type,
            group_id=access.grants[code].group_id,
            group_code=access.grants[code].group_code,
            group_name=access.grants[code].group_name,
            depth=access.grants[code].depth,
        )
        for code, allowed in sorted(access.allowed.items())
    ]

    group_items: list[GroupOut] = []
    if groups:
        loaded = list(
            (
                await session.execute(
                    select(UserGroup)
                    .options(*_options())
                    .where(UserGroup.id.in_([group.id for group in groups]))
                    .order_by(UserGroup.depth, UserGroup.name)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        group_items = [
            GroupOut(
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
                members_count=len(group.memberships),
                permissions_count=len(group.permission_links),
                created_at=group.created_at,
            )
            for group in loaded
        ]

    return MyPermissionsOut(
        user_id=current_user.id,
        role=current_user.role,
        permissions=access.codes,
        denied=[code for code, allowed in access.allowed.items() if not allowed],
        details=details,
        groups=group_items,
    )


@router.get(
    "/services",
    response_model=MyServicesOut,
    summary="Доступные пользователю сервисы",
)
async def my_services(current_user: CurrentUser, session: SessionDep):
    rows = await visible_services(session, current_user)
    items = [
        EffectiveServiceOut(
            code=service.code,
            name=service.name,
            description=service.description,
            icon=service.icon,
            category=service.category,
            api_prefix=service.api_prefix,
            status=service.status,
            enabled=state.enabled,
            source=state.source,
            permission_codes=granted,
        )
        for service, state, granted in rows
    ]
    return MyServicesOut(items=items, total=len(items))
