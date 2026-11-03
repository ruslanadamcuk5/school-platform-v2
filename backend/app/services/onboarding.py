"""Personalised onboarding curriculum and progress persistence."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iam import User
from app.models.onboarding import OnboardingModuleProgress, OnboardingProfile
from app.services.access import (
    EffectivePermissions,
    ServiceState,
    effective_permissions,
    legacy_allows,
    user_service_states,
)
from app.services.onboarding_catalog import (
    CATALOG_VERSION,
    OnboardingModule,
    OnboardingStep,
    get_module,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _allowed(user: User, access: EffectivePermissions, code: str) -> bool:
    if access.can(code):
        return True
    # The transitional bridge is authoritative only while the account has no
    # group memberships, exactly as in the API permission dependency.
    return access.group_count == 0 and legacy_allows(user.role, code)


def module_is_eligible(
    user: User,
    module: OnboardingModule,
    states: dict[str, ServiceState],
    access: EffectivePermissions,
) -> bool:
    if module.roles is not None and user.role not in module.roles:
        return False
    state = states.get(module.service_code)
    if state is None or not state.enabled:
        return False
    if module.required_permissions and not any(
        _allowed(user, access, code) for code in module.required_permissions
    ):
        return False
    return True


@dataclass(frozen=True)
class CurriculumContext:
    states: dict[str, ServiceState]
    access: EffectivePermissions


async def curriculum_context(
    session: AsyncSession, user: User
) -> CurriculumContext:
    return CurriculumContext(
        states=await user_service_states(session, user),
        access=await effective_permissions(session, user),
    )


async def personalized_modules(
    session: AsyncSession, user: User
) -> tuple[list[OnboardingModule], CurriculumContext]:
    """Return modules the learner is entitled to see right now."""
    context = await curriculum_context(session, user)
    from app.services.onboarding_catalog import MODULES

    visible = [
        module
        for module in MODULES
        if module_is_eligible(user, module, context.states, context.access)
    ]
    visible.sort(
        key=lambda item: (
            _stage_order(item.stage),
            item.estimated_minutes,
            item.title,
        )
    )
    return visible, context


def _stage_order(stage: str) -> int:
    order = {
        "start": 0,
        "core": 1,
        "daily": 2,
        "management": 3,
        "advanced": 4,
    }
    return order.get(stage, 99)


async def ensure_profile(
    session: AsyncSession,
    user: User,
    known_service_codes: set[str] | None = None,
) -> OnboardingProfile:
    profile = (
        await session.execute(
            select(OnboardingProfile).where(OnboardingProfile.user_id == user.id)
        )
    ).scalar_one_or_none()
    stamp = now_utc()
    if profile is None:
        profile = OnboardingProfile(
            user_id=user.id,
            known_service_codes=sorted(known_service_codes or set()),
            catalog_version=CATALOG_VERSION,
            last_seen_at=stamp,
        )
        session.add(profile)
        await session.flush()
        return profile

    # A profile created before the catalogue was populated should not mark
    # every existing module as new.
    if not profile.known_service_codes and known_service_codes:
        profile.known_service_codes = sorted(known_service_codes)
    profile.catalog_version = CATALOG_VERSION
    profile.last_seen_at = stamp
    return profile


async def progress_by_module(
    session: AsyncSession, user_id: uuid.UUID
) -> dict[str, OnboardingModuleProgress]:
    rows = (
        await session.execute(
            select(OnboardingModuleProgress).where(
                OnboardingModuleProgress.user_id == user_id
            )
        )
    ).scalars().all()
    return {row.module_code: row for row in rows}


@dataclass
class PersonalizedModule:
    module: OnboardingModule
    progress: OnboardingModuleProgress | None
    is_addon: bool


async def personalized_state(
    session: AsyncSession, user: User
) -> tuple[
    list[PersonalizedModule],
    OnboardingProfile,
    CurriculumContext,
]:
    modules, context = await personalized_modules(session, user)
    known_now = {module.service_code for module in modules}
    profile = await ensure_profile(session, user, known_now)
    progresses = await progress_by_module(session, user.id)
    known = set(profile.known_service_codes or [])
    items = [
        PersonalizedModule(
            module=module,
            progress=progresses.get(module.code),
            is_addon=bool(known) and module.service_code not in known,
        )
        for module in modules
    ]
    return items, profile, context


def next_step(module: OnboardingModule, completed: set[str]) -> OnboardingStep | None:
    for step in module.steps:
        if step.code not in completed:
            return step
    return None


def module_progress_percent(
    module: OnboardingModule, progress: OnboardingModuleProgress | None
) -> int:
    if progress is None:
        return 0
    if progress.status == "completed":
        return 100
    completed = set(progress.completed_step_codes or [])
    if not module.steps:
        return 0
    return round(len(completed) / len(module.steps) * 100)


async def start_module(
    session: AsyncSession, user: User, module_code: str
) -> tuple[OnboardingModule, OnboardingModuleProgress, OnboardingProfile]:
    modules, context = await personalized_modules(session, user)
    module = next((item for item in modules if item.code == module_code), None)
    if module is None:
        raise LookupError("Module is not available for this user")
    profile = await ensure_profile(
        session, user, {item.service_code for item in modules}
    )
    progress = (
        await session.execute(
            select(OnboardingModuleProgress).where(
                OnboardingModuleProgress.user_id == user.id,
                OnboardingModuleProgress.module_code == module.code,
            )
        )
    ).scalar_one_or_none()
    stamp = now_utc()
    if progress is None:
        first = module.steps[0] if module.steps else None
        progress = OnboardingModuleProgress(
            user_id=user.id,
            module_code=module.code,
            service_code=module.service_code,
            status="in_progress" if first else "completed",
            current_step_code=first.code if first else None,
            completed_step_codes=[],
            started_at=stamp,
            last_activity_at=stamp,
            completed_at=None if first else stamp,
        )
        session.add(progress)
    elif progress.status == "not_started":
        progress.status = "in_progress"
        progress.started_at = progress.started_at or stamp
        progress.last_activity_at = stamp
        if progress.current_step_code is None:
            first = next_step(module, set(progress.completed_step_codes or []))
            progress.current_step_code = first.code if first else None

    known = set(profile.known_service_codes or [])
    if module.service_code not in known:
        profile.known_service_codes = sorted({*known, module.service_code})
    await session.flush()
    return module, progress, profile


async def complete_step(
    session: AsyncSession,
    user: User,
    module_code: str,
    step_code: str,
) -> tuple[OnboardingModule, OnboardingModuleProgress, OnboardingProfile]:
    module, progress, profile = await start_module(session, user, module_code)
    step = next((item for item in module.steps if item.code == step_code), None)
    if step is None:
        raise LookupError("Unknown onboarding step")

    completed = set(progress.completed_step_codes or [])
    completed.add(step.code)
    ordered = [item.code for item in module.steps if item.code in completed]
    progress.completed_step_codes = ordered
    progress.last_activity_at = now_utc()

    remainder = next_step(module, set(ordered))
    if remainder is None:
        progress.status = "completed"
        progress.current_step_code = None
        progress.completed_at = progress.completed_at or now_utc()
    else:
        progress.status = "in_progress"
        progress.current_step_code = remainder.code
        progress.completed_at = None

    await session.flush()
    return module, progress, profile


async def reset_user_modules(
    session: AsyncSession, user_id: uuid.UUID
) -> int:
    rows = (
        await session.execute(
            select(OnboardingModuleProgress).where(
                OnboardingModuleProgress.user_id == user_id
            )
        )
    ).scalars().all()
    for row in rows:
        row.status = "not_started"
        row.current_step_code = None
        row.completed_step_codes = []
        row.started_at = None
        row.last_activity_at = None
        row.completed_at = None
    await session.flush()
    return len(rows)


def module_by_code(code: str) -> OnboardingModule | None:
    return get_module(code)
