"""Hierarchical access resolution for groups and platform services.

The module keeps the decision logic pure where possible so it can be unit
tested without a database, and adds thin async loaders for request handling.

Resolution rules
----------------
Permissions
    1. A user receives permissions from all active groups they belong to.
    2. Groups inherit from their explicit ``parent_id`` chain and from groups
       of the same functional category at every ancestor organisational scope
       (class → school → city → region → country).
    3. The most specific scope wins.  At the same depth an explicit ``deny``
       wins over ``allow``.
    4. Expired memberships and expired permission grants are ignored.

Services
    1. A service is enabled when the most specific activation for the user's
       scope tree says so.
    2. If there is no activation, the service default applies.
    3. Core services (IAM, org, system, audit) can never be switched off.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scopes import COUNTRY_SCOPE_ID, SCOPE_DEPTH
from app.models.iam import (
    GroupMembership,
    GroupPermission,
    Permission,
    User,
    UserGroup,
)
from app.models.org import City, ClassMembership, School, SchoolClass
from app.models.system import Service, ServiceActivation
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------- pure
@dataclass(frozen=True)
class PermissionGrant:
    code: str
    effect: str
    depth: int
    scope_type: str
    group_id: uuid.UUID
    group_code: str
    group_name: str


@dataclass
class EffectivePermissions:
    """Resolved permission map plus the grants that produced it."""

    allowed: dict[str, bool] = field(default_factory=dict)
    grants: dict[str, PermissionGrant] = field(default_factory=dict)
    group_count: int = 0

    def can(self, code: str) -> bool:
        return self.allowed.get(code, False)

    @property
    def codes(self) -> list[str]:
        return sorted(code for code, allowed in self.allowed.items() if allowed)


# Transitional bridge for accounts that existed before group-based access was
# introduced.  It applies only while the user has no group memberships at all,
# so moving a user into a group immediately switches the account to the new
# group-based model.  The map is deliberately explicit and auditable.
LEGACY_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "superadmin": ("*",),
    "admin": (
        "iam.",
        "org.",
        "admin.",
        "system.",
        "audit.",
        "lms.",
        "assessment.",
        "journal.",
        "library.",
        "analytics.",
        "communication.",
    ),
    "methodologist": (
        "lms.",
        "assessment.",
        "library.",
        "journal.",
        "analytics.reports.read",
        "analytics.bi.read",
    ),
    "teacher": (
        "lms.content.read",
        "assessment.quizzes.read",
        "assessment.quizzes.write",
        "assessment.assignments.create",
        "assessment.submissions.grade",
        "assessment.results.read",
        "journal.",
        "library.",
    ),
    "student": (
        "lms.content.read",
        "assessment.submissions.submit",
        "assessment.results.read",
        "journal.schedule.read",
        "journal.grades.read",
        "journal.attendance.read",
        "library.catalog.read",
        "communication.chat.use",
    ),
    "parent": (
        "journal.schedule.read",
        "journal.grades.read",
        "journal.attendance.read",
        "assessment.results.read",
        "library.catalog.read",
        "communication.chat.use",
    ),
    "psychologist": (
        "safety.",
        "journal.",
        "iam.profile.read",
        "communication.chat.use",
    ),
    "secretary": (
        "documents.",
        "org.",
        "iam.users.read",
        "iam.profile.read",
    ),
}


def legacy_allows(role: str, code: str) -> bool:
    for pattern in LEGACY_ROLE_PERMISSIONS.get(role, ()):
        if pattern == "*" or code == pattern or (
            pattern.endswith(".") and code.startswith(pattern)
        ):
            return True
    return False


def resolve_permissions(grants: Iterable[PermissionGrant]) -> EffectivePermissions:
    """Pick the winning grant for every permission code."""
    grouped: dict[str, list[PermissionGrant]] = defaultdict(list)
    for grant in grants:
        grouped[grant.code].append(grant)

    resolved = EffectivePermissions()
    for code, items in grouped.items():
        # Most specific first; deny before allow on a tie.
        items.sort(key=lambda item: (-item.depth, 0 if item.effect == "deny" else 1))
        winner = items[0]
        resolved.allowed[code] = winner.effect == "allow"
        resolved.grants[code] = winner
    return resolved


@dataclass(frozen=True)
class ServiceState:
    code: str
    enabled: bool
    source: str
    depth: int | None = None
    scope_type: str | None = None
    scope_id: uuid.UUID | None = None
    config: dict = field(default_factory=dict)


def pick_service_state(
    code: str,
    *,
    default_enabled: bool,
    is_core: bool,
    activations: Sequence[ServiceActivation] = (),
) -> ServiceState:
    """Choose the most specific activation for one service."""
    published = SERVICE_BY_CODE.get(code)
    if is_core or (published is not None and published.is_core):
        return ServiceState(code=code, enabled=True, source="core")
    if not activations:
        return ServiceState(code=code, enabled=default_enabled, source="default")
    winner = max(activations, key=lambda item: item.depth)
    return ServiceState(
        code=code,
        enabled=winner.enabled,
        source="activation",
        depth=winner.depth,
        scope_type=winner.scope_type,
        scope_id=winner.scope_id,
        config=dict(winner.config or {}),
    )


def scope_within(
    target: tuple[str, uuid.UUID], ancestors: set[tuple[str, uuid.UUID]]
) -> bool:
    """Return True when the target scope is the scope or a descendant of it."""
    return target in ancestors


# ------------------------------------------------------------------ loaders
async def _scope_ancestors(
    session: AsyncSession, scope_type: str, scope_id: uuid.UUID
) -> set[tuple[str, uuid.UUID]]:
    """Return the scope itself and every ancestor up to the country."""
    result: set[tuple[str, uuid.UUID]] = {
        ("country", COUNTRY_SCOPE_ID),
        (scope_type, scope_id),
    }
    if scope_type == "country":
        return result
    if scope_type == "region":
        return result

    if scope_type == "city":
        city = await session.get(City, scope_id)
        if city is not None:
            result.add(("region", city.region_id))
        return result

    if scope_type == "school":
        school = await session.get(School, scope_id)
        if school is not None and school.city_id is not None:
            result.add(("city", school.city_id))
            city = await session.get(City, school.city_id)
            if city is not None:
                result.add(("region", city.region_id))
        return result

    if scope_type == "class":
        school_class = await session.get(SchoolClass, scope_id)
        if school_class is not None:
            result.add(("school", school_class.school_id))
            school = await session.get(School, school_class.school_id)
            if school is not None and school.city_id is not None:
                result.add(("city", school.city_id))
                city = await session.get(City, school.city_id)
                if city is not None:
                    result.add(("region", city.region_id))
    return result


async def scope_ancestors(
    session: AsyncSession, scope_type: str, scope_id: uuid.UUID
) -> set[tuple[str, uuid.UUID]]:
    """Public wrapper used by the service catalog API."""
    return await _scope_ancestors(session, scope_type, scope_id)


async def user_scope_keys(
    session: AsyncSession, user: User
) -> set[tuple[str, uuid.UUID]]:
    """All organisational scopes the user is attached to, plus ancestors."""
    keys: set[tuple[str, uuid.UUID]] = {("country", COUNTRY_SCOPE_ID)}
    if user.school_id is not None:
        keys |= await _scope_ancestors(session, "school", user.school_id)

    memberships = (
        await session.execute(
            select(ClassMembership.class_id).where(
                ClassMembership.user_id == user.id,
                ClassMembership.left_at.is_(None),
            )
        )
    ).scalars().all()
    for class_id in memberships:
        keys |= await _scope_ancestors(session, "class", class_id)
    return keys


async def _direct_groups(
    session: AsyncSession, user: User
) -> list[UserGroup]:
    stamp = now_utc()
    stmt = (
        select(UserGroup)
        .join(GroupMembership, GroupMembership.group_id == UserGroup.id)
        .where(
            GroupMembership.user_id == user.id,
            UserGroup.is_active.is_(True),
            (GroupMembership.expires_at.is_(None))
            | (GroupMembership.expires_at > stamp),
        )
    )
    return list((await session.execute(stmt)).scalars().unique().all())


async def _parent_chain(
    session: AsyncSession, groups: Iterable[UserGroup]
) -> list[UserGroup]:
    seen = {group.id: group for group in groups}
    frontier = {group.parent_id for group in groups if group.parent_id is not None}
    for _ in range(20):
        if not frontier:
            break
        rows = (
            await session.execute(
                select(UserGroup).where(
                    UserGroup.id.in_(frontier),
                    UserGroup.is_active.is_(True),
                )
            )
        ).scalars().all()
        frontier = set()
        for group in rows:
            if group.id in seen:
                continue
            seen[group.id] = group
            if group.parent_id is not None and group.parent_id not in seen:
                frontier.add(group.parent_id)
    return list(seen.values())


async def _organisational_groups(
    session: AsyncSession,
    categories: set[str],
    scope_keys: set[tuple[str, uuid.UUID]],
) -> list[UserGroup]:
    if not categories or not scope_keys:
        return []
    stmt = select(UserGroup).where(
        UserGroup.is_active.is_(True),
        UserGroup.category.in_(categories),
        tuple_(UserGroup.scope_type, UserGroup.scope_id).in_(scope_keys),
    )
    return list((await session.execute(stmt)).scalars().unique().all())


async def load_user_groups(
    session: AsyncSession, user: User
) -> list[UserGroup]:
    """Return direct groups plus inherited groups for a user."""
    direct = await _direct_groups(session, user)
    if not direct:
        return []
    categories = {group.category for group in direct}
    scopes = await user_scope_keys(session, user)
    inherited = await _organisational_groups(session, categories, scopes)
    merged = await _parent_chain(session, [*direct, *inherited])
    return [group for group in merged if group.is_active]


async def effective_permissions(
    session: AsyncSession, user: User
) -> EffectivePermissions:
    groups = await load_user_groups(session, user)
    if not groups:
        return EffectivePermissions()

    stamp = now_utc()
    rows = (
        await session.execute(
            select(
                GroupPermission.group_id,
                Permission.code,
                GroupPermission.effect,
                GroupPermission.expires_at,
            )
            .join(Permission, Permission.id == GroupPermission.permission_id)
            .where(GroupPermission.group_id.in_([group.id for group in groups]))
        )
    ).all()

    by_id = {group.id: group for group in groups}
    grants: list[PermissionGrant] = []
    for group_id, code, effect, expires_at in rows:
        if expires_at is not None and expires_at <= stamp:
            continue
        group = by_id.get(group_id)
        if group is None:
            continue
        grants.append(
            PermissionGrant(
                code=code,
                effect=effect,
                depth=SCOPE_DEPTH.get(group.scope_type, 0),
                scope_type=group.scope_type,
                group_id=group.id,
                group_code=group.code,
                group_name=group.name,
            )
        )
    resolved = resolve_permissions(grants)
    resolved.group_count = len(groups)
    return resolved


async def management_scopes(
    session: AsyncSession, user: User
) -> set[tuple[str, uuid.UUID]]:
    """Scopes where the user may administer groups and services."""
    if user.role == "superadmin":
        return {("country", COUNTRY_SCOPE_ID)}
    groups = await load_user_groups(session, user)
    if not groups:
        return set()
    rows = (
        await session.execute(
            select(GroupPermission.group_id, Permission.code)
            .join(Permission, Permission.id == GroupPermission.permission_id)
            .where(
                GroupPermission.group_id.in_([group.id for group in groups]),
                GroupPermission.effect == "allow",
            )
        )
    ).all()
    manage_codes = {
        "iam.groups.write",
        "system.services.write",
        "admin.school.manage",
        "admin.region.manage",
        "admin.country.manage",
    }
    allowed_group_ids = {
        group_id for group_id, code in rows if code in manage_codes
    }
    scopes: set[tuple[str, uuid.UUID]] = set()
    for group in groups:
        if group.id in allowed_group_ids:
            scopes.add((group.scope_type, group.scope_id))
    if user.role in {"admin", "methodologist"} and user.school_id is not None:
        scopes.add(("school", user.school_id))
    return scopes


async def can_manage_scope(
    session: AsyncSession,
    user: User,
    scope_type: str,
    scope_id: uuid.UUID,
) -> bool:
    if user.role == "superadmin":
        return True
    if scope_type not in SCOPE_DEPTH:
        return False
    allowed = await management_scopes(session, user)
    if not allowed:
        return False
    target_scopes = await _scope_ancestors(session, scope_type, scope_id)
    return any(scope in target_scopes for scope in allowed)


async def user_service_scope_keys(
    session: AsyncSession, user: User
) -> set[tuple[str, uuid.UUID]]:
    """Scopes used for service activation.

    Class scopes come from the user's groups rather than from
    ``org.class_memberships``.  This keeps service checks independent from the
    class roster query and still supports class-level activations when a class
    group is assigned.
    """
    keys: set[tuple[str, uuid.UUID]] = {("country", COUNTRY_SCOPE_ID)}
    if user.school_id is not None:
        keys |= await _scope_ancestors(session, "school", user.school_id)
    for group in await load_user_groups(session, user):
        keys.add((group.scope_type, group.scope_id))
    return keys


async def user_service_states(
    session: AsyncSession, user: User
) -> dict[str, ServiceState]:
    """Resolve every catalogued service for the user's scope tree."""
    scopes = await user_service_scope_keys(session, user)
    services = list(
        (await session.execute(select(Service))).scalars().all()
    )
    if not services:
        services = []
        for manifest in SERVICE_BY_CODE.values():
            # Fallback for a database that has not been seeded yet.
            services.append(
                Service(
                    code=manifest.code,
                    name=manifest.name,
                    description=manifest.description,
                    category=manifest.category,
                    api_prefix=manifest.api_prefix,
                    icon=manifest.icon,
                    default_enabled=manifest.default_enabled,
                    is_core=manifest.is_core,
                    status=manifest.status,
                    manifest=manifest.manifest_payload,
                )
            )

    activations = list(
        (
            await session.execute(
                select(ServiceActivation).where(
                    tuple_(
                        ServiceActivation.scope_type,
                        ServiceActivation.scope_id,
                    ).in_(scopes)
                )
            )
        ).scalars().all()
    )
    by_service: dict[str, list[ServiceActivation]] = defaultdict(list)
    for activation in activations:
        by_service[activation.service_code].append(activation)

    states: dict[str, ServiceState] = {}
    for service in services:
        states[service.code] = pick_service_state(
            service.code,
            default_enabled=service.default_enabled,
            is_core=service.is_core,
            activations=by_service.get(service.code, []),
        )
    return states


def service_permission_codes(service_code: str, permissions: Iterable[str]) -> list[str]:
    """Permission codes that belong to ``service_code``."""
    prefix = f"{service_code}."
    return sorted(code for code in permissions if code.startswith(prefix))


async def visible_services(
    session: AsyncSession, user: User
) -> list[tuple[Service, ServiceState, list[str]]]:
    """Services enabled for the user and backed by at least one permission."""
    states = await user_service_states(session, user)
    access = await effective_permissions(session, user)
    services = list((await session.execute(select(Service))).scalars().all())
    if not services:
        services = [
            Service(
                code=manifest.code,
                name=manifest.name,
                description=manifest.description,
                category=manifest.category,
                api_prefix=manifest.api_prefix,
                icon=manifest.icon,
                default_enabled=manifest.default_enabled,
                is_core=manifest.is_core,
                status=manifest.status,
                manifest=manifest.manifest_payload,
            )
            for manifest in SERVICE_BY_CODE.values()
        ]

    result: list[tuple[Service, ServiceState, list[str]]] = []
    allowed_codes = access.codes
    for service in services:
        state = states.get(service.code)
        if state is None or not state.enabled:
            continue
        published = SERVICE_BY_CODE.get(service.code)
        known_codes = (
            published.permission_codes
            if published is not None
            else tuple(
                item["code"]
                for item in (service.manifest or {}).get("permissions", [])
            )
        )
        granted = [
            code for code in known_codes if code in allowed_codes
        ]
        has_any = bool(granted)
        open_service = not known_codes or service.is_core
        if not has_any and not open_service:
            continue
        result.append((service, state, granted))
    result.sort(key=lambda item: (item[0].category, item[0].name))
    return result


def unknown_permission(code: str) -> bool:
    return code not in PERMISSION_BY_CODE
