"""Idempotent seed for the pilot database.

Run from the backend directory:

    python -m app.db.seed

The script creates the pilot school, grades 1-11, one superadmin account and
the platform baseline:

* the permission catalog published by every service;
* the service catalog and country-level activations;
* country, school and class groups with inherited permissions;
* group memberships derived from the legacy ``users.role`` field.

It never overwrites an existing user's password.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.scopes import COUNTRY_SCOPE_ID, SCOPE_DEPTH
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.iam import (
    GroupMembership,
    GroupPermission,
    Permission,
    User,
    UserGroup,
)
from app.models.org import School, SchoolClass
from app.models.system import Service, ServiceActivation
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE, SERVICES

ROLE_CATEGORY = {
    "student": "students",
    "teacher": "teachers",
    "admin": "administration",
    "methodologist": "methodologists",
    "psychologist": "psychologists",
    "secretary": "secretaries",
    "parent": "parents",
}

CATEGORY_NAME = {
    "students": "Ученики",
    "teachers": "Учителя",
    "administration": "Администрация",
    "methodologists": "Методисты",
    "psychologists": "Психологи",
    "secretaries": "Секретариат",
    "parents": "Родители",
    "other": "Прочие",
}

# Permissions granted to school-level groups.  The legacy role bridge is used
# only to build the initial matrix; afterwards administrators edit groups.
ROLE_FOR_CATEGORY = {
    "students": "student",
    "teachers": "teacher",
    "administration": "admin",
    "methodologists": "methodologist",
    "psychologists": "psychologist",
    "secretaries": "secretary",
    "parents": "parent",
}


async def _upsert_permissions(session) -> int:
    existing = {
        code
        for code in (
            await session.execute(select(Permission.code))
        ).scalars().all()
    }
    created = 0
    for code, spec in PERMISSION_BY_CODE.items():
        if code in existing:
            continue
        session.add(
            Permission(
                code=spec.code,
                name=spec.name,
                description=None,
                service_code=spec.code.split(".", 1)[0],
                category=spec.category,
                is_system=True,
            )
        )
        created += 1
    await session.flush()
    return created


async def _upsert_services(session) -> int:
    existing = {
        code
        for code in (
            await session.execute(select(Service.code))
        ).scalars().all()
    }
    created = 0
    for manifest in SERVICES:
        if manifest.code in existing:
            continue
        session.add(
            Service(
                code=manifest.code,
                name=manifest.name,
                description=manifest.description,
                version=manifest.version,
                category=manifest.category,
                api_prefix=manifest.api_prefix,
                icon=manifest.icon,
                default_enabled=manifest.default_enabled,
                is_core=manifest.is_core,
                status=manifest.status,
                manifest=manifest.manifest_payload,
            )
        )
        created += 1
    await session.flush()
    return created


async def _upsert_country_activations(session, admin: User | None) -> int:
    existing = {
        code
        for code in (
            await session.execute(
                select(ServiceActivation.service_code).where(
                    ServiceActivation.scope_type == "country",
                    ServiceActivation.scope_id == COUNTRY_SCOPE_ID,
                )
            )
        ).scalars().all()
    }
    created = 0
    for manifest in SERVICES:
        if manifest.code in existing:
            continue
        enabled = manifest.is_core or manifest.default_enabled
        session.add(
            ServiceActivation(
                service_code=manifest.code,
                scope_type="country",
                scope_id=COUNTRY_SCOPE_ID,
                depth=SCOPE_DEPTH["country"],
                enabled=enabled,
                config={},
                updated_by=admin.id if admin else None,
            )
        )
        created += 1
    await session.flush()
    return created


async def _get_or_create_group(
    session,
    *,
    code: str,
    name: str,
    category: str,
    scope_type: str,
    scope_id,
    parent_id=None,
    is_system: bool = True,
) -> UserGroup:
    group = (
        await session.execute(
            select(UserGroup).where(
                UserGroup.scope_type == scope_type,
                UserGroup.scope_id == scope_id,
                UserGroup.code == code,
            )
        )
    ).scalar_one_or_none()
    if group is not None:
        return group
    group = UserGroup(
        code=code,
        name=name,
        description=None,
        category=category,
        scope_type=scope_type,
        scope_id=scope_id,
        depth=SCOPE_DEPTH[scope_type],
        parent_id=parent_id,
        is_system=is_system,
        is_active=True,
        meta={},
    )
    session.add(group)
    await session.flush()
    return group


async def _grant_permissions(
    session, group: UserGroup, codes: set[str], granted_by: User | None
) -> int:
    existing = {
        permission_id
        for permission_id in (
            await session.execute(
                select(GroupPermission.permission_id).where(
                    GroupPermission.group_id == group.id
                )
            )
        ).scalars().all()
    }
    permissions = list(
        (
            await session.execute(
                select(Permission).where(Permission.code.in_(codes))
            )
        )
        .scalars()
        .all()
    )
    created = 0
    for permission in permissions:
        if permission.id in existing:
            continue
        session.add(
            GroupPermission(
                group_id=group.id,
                permission_id=permission.id,
                effect="allow",
                granted_by=granted_by.id if granted_by else None,
            )
        )
        created += 1
    await session.flush()
    return created


async def _add_membership(
    session, group: UserGroup, user: User, assigned_by: User | None
) -> bool:
    exists = (
        await session.execute(
            select(GroupMembership.id).where(
                GroupMembership.group_id == group.id,
                GroupMembership.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        return False
    session.add(
        GroupMembership(
            group_id=group.id,
            user_id=user.id,
            assigned_by=assigned_by.id if assigned_by else None,
            is_primary=True,
        )
    )
    return True


async def seed() -> None:
    if not settings.admin_password:
        raise RuntimeError(
            "ADMIN_PASSWORD is not set. Add it to .env before running the seed."
        )

    async with AsyncSessionLocal() as session:
        school = (
            await session.execute(
                select(School).where(School.code == settings.seed_school_code)
            )
        ).scalar_one_or_none()
        if school is None:
            school = School(
                code=settings.seed_school_code,
                name=settings.seed_school_name,
                short_name="Пилотная школа",
                city=settings.seed_school_city,
                address="",
                is_active=True,
            )
            session.add(school)
            await session.flush()
            print(f"created school: {school.name} ({school.id})")
        else:
            print(f"school exists: {school.name} ({school.id})")

        existing_classes = (
            await session.execute(
                select(SchoolClass.grade, SchoolClass.letter).where(
                    SchoolClass.school_id == school.id,
                    SchoolClass.academic_year == settings.seed_academic_year,
                )
            )
        ).all()
        existing = {(grade, letter) for grade, letter in existing_classes}
        created_classes = 0
        for grade in range(1, 12):
            if (grade, "А") not in existing:
                session.add(
                    SchoolClass(
                        school_id=school.id,
                        grade=grade,
                        letter="А",
                        academic_year=settings.seed_academic_year,
                        is_active=True,
                    )
                )
                created_classes += 1
        print(f"classes created: {created_classes}")

        admin = (
            await session.execute(
                select(User).where(User.login == settings.admin_login)
            )
        ).scalar_one_or_none()
        if admin is None:
            admin = User(
                school_id=None,
                login=settings.admin_login,
                email=settings.admin_email or None,
                password_hash=hash_password(settings.admin_password),
                role="superadmin",
                first_name="Администратор",
                last_name="Платформы",
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.flush()
            print(f"created superadmin: {admin.login} ({admin.id})")
        else:
            print(f"user exists, password unchanged: {admin.login} ({admin.id})")

        permissions_created = await _upsert_permissions(session)
        services_created = await _upsert_services(session)
        activations_created = await _upsert_country_activations(session, admin)
        print(
            "catalog: "
            f"permissions +{permissions_created}, services +{services_created}, "
            f"activations +{activations_created}"
        )

        # Country administration group.  The superadmin inherits every
        # permission through it, so the group model works from day one.
        country_admin = await _get_or_create_group(
            session,
            code="administration",
            name="Республиканская администрация",
            category="administration",
            scope_type="country",
            scope_id=COUNTRY_SCOPE_ID,
        )
        all_codes = set(PERMISSION_BY_CODE)
        await _grant_permissions(session, country_admin, all_codes, admin)
        await _add_membership(session, country_admin, admin, admin)

        # School-level groups for every functional category.
        school_groups: dict[str, UserGroup] = {}
        for category, role_name in ROLE_FOR_CATEGORY.items():
            group = await _get_or_create_group(
                session,
                code=category,
                name=CATEGORY_NAME[category],
                category=category,
                scope_type="school",
                scope_id=school.id,
                parent_id=country_admin.id,
            )
            school_groups[category] = group
            codes = {
                code
                for code in PERMISSION_BY_CODE
                if legacy_allows(role_name, code)
            }
            await _grant_permissions(session, group, codes, admin)

        # Class-level groups inherit from the matching school group.
        class_rows = (
            await session.execute(
                select(SchoolClass).where(
                    SchoolClass.school_id == school.id,
                    SchoolClass.academic_year == settings.seed_academic_year,
                )
            )
        ).scalars().all()
        for school_class in class_rows:
            for category in ("students", "teachers"):
                await _get_or_create_group(
                    session,
                    code=category,
                    name=f"{CATEGORY_NAME[category]} {school_class.display_name}",
                    category=category,
                    scope_type="class",
                    scope_id=school_class.id,
                    parent_id=school_groups[category].id,
                )

        # Map every existing school user to their role group.
        users = list(
            (
                await session.execute(
                    select(User).where(
                        User.school_id == school.id,
                        User.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        memberships = 0
        for user in users:
            category = ROLE_CATEGORY.get(user.role)
            if category is None or category not in school_groups:
                continue
            if await _add_membership(session, school_groups[category], user, admin):
                memberships += 1
        print(f"groups: school users attached: {memberships}")

        await session.commit()

    await engine.dispose()
    print("seed complete")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        raise
