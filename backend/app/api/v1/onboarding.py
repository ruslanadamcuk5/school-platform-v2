"""Personalised onboarding API and progress reports."""
from __future__ import annotations

import csv
import io
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, SessionDep, require_permission, require_service
from app.models.iam import ROLE_VALUES, User, UserRelation
from app.models.journal import LessonSchedule
from app.models.onboarding import OnboardingModuleProgress, OnboardingProfile
from app.models.org import (
    City,
    ClassMembership,
    School,
    SchoolClass,
    TeacherSubject,
)
from app.schemas.common import Message
from app.schemas.onboarding import (
    OnboardingModuleOut,
    OnboardingOverviewOut,
    OnboardingProgressOut,
    OnboardingReportSummaryOut,
    OnboardingReportUserOut,
    OnboardingReportUsersOut,
    OnboardingStageOut,
    OnboardingStepOut,
)
from app.services.access import management_scopes
from app.services.audit import add_audit_event
from app.services.onboarding import (
    complete_step,
    module_progress_percent,
    personalized_state,
    reset_user_modules,
    start_module,
)
from app.services.onboarding_catalog import CATALOG_VERSION, STAGES
from app.services.registry import SERVICE_BY_CODE

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

LEARNER_DEPS = [
    Depends(require_service("onboarding")),
    Depends(require_permission("onboarding.courses.read")),
]
REPORT_DEPS = [Depends(require_permission("onboarding.progress.read"))]
MANAGE_DEPS = [Depends(require_permission("onboarding.progress.manage"))]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _step_out(step, completed: set[str]) -> OnboardingStepOut:
    return OnboardingStepOut(
        code=step.code,
        title=step.title,
        body=step.body,
        target=step.target,
        route=step.route,
        tip=step.tip,
        action=step.action,
        duration_seconds=step.duration_seconds,
        completed=step.code in completed,
    )


def _module_out(item) -> OnboardingModuleOut:
    module = item.module
    progress = item.progress
    completed = set(progress.completed_step_codes or []) if progress else set()
    status_value = progress.status if progress else "not_started"
    total_steps = len(module.steps)
    completed_steps = len(completed)
    percent = module_progress_percent(module, progress)
    manifest = SERVICE_BY_CODE.get(module.service_code)
    return OnboardingModuleOut(
        code=module.code,
        service_code=module.service_code,
        service_name=manifest.name if manifest else module.service_code,
        service_icon=manifest.icon if manifest else module.icon,
        stage=module.stage,
        title=module.title,
        description=module.description,
        icon=module.icon,
        estimated_minutes=module.estimated_minutes,
        roles=list(module.roles) if module.roles else None,
        is_addon=item.is_addon,
        status=status_value,
        current_step_code=(
            None
            if progress and progress.status == "completed"
            else (
                progress.current_step_code
                if progress and progress.current_step_code
                else (module.steps[0].code if module.steps else None)
            )
        ),
        completed_steps=completed_steps,
        total_steps=total_steps,
        progress_percent=percent,
        started_at=progress.started_at if progress else None,
        completed_at=progress.completed_at if progress else None,
        last_activity_at=progress.last_activity_at if progress else None,
        steps=[_step_out(step, completed) for step in module.steps],
    )


def _progress_out(module, progress) -> OnboardingProgressOut:
    completed = set(progress.completed_step_codes or [])
    return OnboardingProgressOut(
        module_code=progress.module_code,
        status=progress.status,
        current_step_code=progress.current_step_code,
        completed_steps=len(completed),
        total_steps=len(module.steps),
        progress_percent=module_progress_percent(module, progress),
        started_at=progress.started_at,
        completed_at=progress.completed_at,
        last_activity_at=progress.last_activity_at,
    )


# ------------------------------------------------------------------ learner
@router.get(
    "/me",
    response_model=OnboardingOverviewOut,
    summary="Персональная программа обучения",
    dependencies=LEARNER_DEPS,
)
async def my_onboarding(
    current_user: CurrentUser,
    session: SessionDep,
) -> OnboardingOverviewOut:
    items, profile, _context = await personalized_state(session, current_user)
    await session.commit()

    modules = [_module_out(item) for item in items]
    by_stage: dict[str, list[OnboardingModuleOut]] = {}
    for module in modules:
        by_stage.setdefault(module.stage, []).append(module)

    stages: list[OnboardingStageOut] = []
    for stage in STAGES:
        stage_modules = by_stage.get(stage["code"], [])
        if not stage_modules:
            continue
        completed = sum(1 for item in stage_modules if item.status == "completed")
        stages.append(
            OnboardingStageOut(
                code=stage["code"],
                title=stage["title"],
                description=stage["description"],
                modules=stage_modules,
                total=len(stage_modules),
                completed=completed,
                progress_percent=round(completed / len(stage_modules) * 100)
                if stage_modules
                else 0,
            )
        )

    total = len(modules)
    completed = sum(1 for item in modules if item.status == "completed")
    in_progress = sum(1 for item in modules if item.status == "in_progress")
    not_started = total - completed - in_progress
    return OnboardingOverviewOut(
        user_id=current_user.id,
        role=current_user.role,
        catalog_version=CATALOG_VERSION,
        generated_at=_now(),
        known_service_codes=sorted(profile.known_service_codes or []),
        stages=stages,
        modules=modules,
        total=total,
        completed=completed,
        in_progress=in_progress,
        not_started=not_started,
        addon_total=sum(1 for item in modules if item.is_addon),
        progress_percent=round(completed / total * 100) if total else 0,
    )


@router.get(
    "/me/modules/{module_code}",
    response_model=OnboardingModuleOut,
    summary="Модуль персональной программы",
    dependencies=LEARNER_DEPS,
)
async def my_module(
    module_code: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> OnboardingModuleOut:
    items, _profile, _context = await personalized_state(session, current_user)
    item = next((entry for entry in items if entry.module.code == module_code), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Training module not found")
    await session.commit()
    return _module_out(item)


@router.post(
    "/me/modules/{module_code}/start",
    response_model=OnboardingProgressOut,
    summary="Начать или продолжить модуль",
    dependencies=LEARNER_DEPS,
)
async def start_my_module(
    module_code: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> OnboardingProgressOut:
    try:
        module, progress, _profile = await start_module(
            session, current_user, module_code
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _progress_out(module, progress)


@router.post(
    "/me/modules/{module_code}/steps/{step_code}/complete",
    response_model=OnboardingProgressOut,
    summary="Завершить шаг обучения",
    dependencies=LEARNER_DEPS,
)
async def complete_my_step(
    module_code: str,
    step_code: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> OnboardingProgressOut:
    try:
        module, progress, _profile = await complete_step(
            session, current_user, module_code, step_code
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _progress_out(module, progress)


# ------------------------------------------------------------------ reports
async def _managed_school_ids(
    session: SessionDep, user: User
) -> set[uuid.UUID] | None:
    """Return visible school ids, or None for unrestricted country access."""
    if user.role == "superadmin":
        return None

    scopes = await management_scopes(session, user)
    if not scopes and user.school_id is not None:
        scopes = {("school", user.school_id)}

    ids: set[uuid.UUID] = set()
    for scope_type, scope_id in scopes:
        if scope_type == "country":
            return None
        if scope_type == "region":
            ids |= set(
                (
                    await session.execute(
                        select(School.id)
                        .join(City, City.id == School.city_id)
                        .where(City.region_id == scope_id)
                    )
                ).scalars().all()
            )
        elif scope_type == "city":
            ids |= set(
                (
                    await session.execute(
                        select(School.id).where(School.city_id == scope_id)
                    )
                ).scalars().all()
            )
        elif scope_type == "school":
            ids.add(scope_id)
        elif scope_type == "class":
            school_class = await session.get(SchoolClass, scope_id)
            if school_class is not None:
                ids.add(school_class.school_id)
    if user.school_id is not None:
        ids.add(user.school_id)
    return ids


async def _teacher_student_ids(
    session: SessionDep, teacher_id: uuid.UUID
) -> set[uuid.UUID]:
    class_ids: set[uuid.UUID] = set()
    class_ids |= set(
        (
            await session.execute(
                select(TeacherSubject.class_id).where(
                    TeacherSubject.teacher_id == teacher_id,
                    TeacherSubject.class_id.is_not(None),
                )
            )
        ).scalars().all()
    )
    class_ids |= set(
        (
            await session.execute(
                select(LessonSchedule.class_id).where(
                    LessonSchedule.teacher_id == teacher_id
                )
            )
        ).scalars().all()
    )
    class_ids |= set(
        (
            await session.execute(
                select(SchoolClass.id).where(
                    SchoolClass.homeroom_teacher_id == teacher_id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        ).scalars().all()
    )
    if not class_ids:
        return set()
    return set(
        (
            await session.execute(
                select(ClassMembership.user_id).where(
                    ClassMembership.class_id.in_(class_ids),
                    ClassMembership.left_at.is_(None),
                )
            )
        ).scalars().all()
    )


async def _parent_child_ids(
    session: SessionDep, parent_id: uuid.UUID
) -> set[uuid.UUID]:
    return set(
        (
            await session.execute(
                select(UserRelation.child_id).where(
                    UserRelation.parent_id == parent_id
                )
            )
        ).scalars().all()
    )


async def _report_conditions(
    session: SessionDep,
    current_user: User,
    *,
    school_id: uuid.UUID | None,
    role: str | None,
    status_filter: str | None,
    search: str | None,
) -> list:
    conditions = [User.deleted_at.is_(None)]

    if current_user.role == "teacher":
        student_ids = await _teacher_student_ids(session, current_user.id)
        conditions.append(User.id.in_(student_ids))
    elif current_user.role == "parent":
        child_ids = await _parent_child_ids(session, current_user.id)
        conditions.append(User.id.in_(child_ids))
    else:
        school_ids = await _managed_school_ids(session, current_user)
        if school_id is not None:
            if school_ids is not None and school_id not in school_ids:
                raise HTTPException(
                    status_code=403,
                    detail="School is outside the report scope",
                )
            conditions.append(User.school_id == school_id)
        elif school_ids is not None:
            conditions.append(User.school_id.in_(school_ids))

    if role:
        if role not in ROLE_VALUES:
            raise HTTPException(status_code=422, detail="Unknown role")
        conditions.append(User.role == role)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.login.ilike(pattern),
                User.last_name.ilike(pattern),
                User.first_name.ilike(pattern),
            )
        )
    return conditions


async def _report_data(
    session: SessionDep,
    current_user: User,
    *,
    school_id: uuid.UUID | None,
    role: str | None,
    status_filter: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[OnboardingReportUserOut], OnboardingReportSummaryOut, int]:
    conditions = await _report_conditions(
        session,
        current_user,
        school_id=school_id,
        role=role,
        status_filter=status_filter,
        search=search,
    )

    addon_count = (
        select(func.count(OnboardingModuleProgress.id))
        .join(
            OnboardingProfile,
            OnboardingProfile.user_id == OnboardingModuleProgress.user_id,
        )
        .where(
            OnboardingModuleProgress.user_id == User.id,
            ~OnboardingProfile.known_service_codes.op("@>")(
                func.jsonb_build_array(OnboardingModuleProgress.service_code)
            ),
        )
        .scalar_subquery()
    )
    progress_agg = (
        select(
            OnboardingModuleProgress.user_id.label("user_id"),
            func.count(OnboardingModuleProgress.id).label("modules_total"),
            func.count(OnboardingModuleProgress.id)
            .filter(OnboardingModuleProgress.status == "completed")
            .label("modules_completed"),
            func.count(OnboardingModuleProgress.id)
            .filter(OnboardingModuleProgress.status == "in_progress")
            .label("modules_in_progress"),
            func.max(OnboardingModuleProgress.last_activity_at).label(
                "last_activity_at"
            ),
        )
        .group_by(OnboardingModuleProgress.user_id)
        .subquery()
    )

    rows = (
        await session.execute(
            select(
                User,
                School.name.label("school_name"),
                func.coalesce(progress_agg.c.modules_total, 0),
                func.coalesce(progress_agg.c.modules_completed, 0),
                func.coalesce(progress_agg.c.modules_in_progress, 0),
                progress_agg.c.last_activity_at,
                func.coalesce(addon_count, 0),
            )
            .outerjoin(progress_agg, progress_agg.c.user_id == User.id)
            .outerjoin(School, School.id == User.school_id)
            .where(*conditions)
            .order_by(User.last_name, User.first_name, User.login)
        )
    ).all()

    items: list[OnboardingReportUserOut] = []
    for (
        user,
        school_name,
        modules_total,
        modules_completed,
        modules_in_progress,
        last_activity_at,
        addon_modules,
    ) in rows:
        total = int(modules_total or 0)
        completed = int(modules_completed or 0)
        in_progress = int(modules_in_progress or 0)
        if total == 0:
            user_status = "not_started"
        elif completed >= total:
            user_status = "completed"
        else:
            user_status = "in_progress"
        if status_filter and user_status != status_filter:
            continue
        items.append(
            OnboardingReportUserOut(
                user_id=user.id,
                login=user.login,
                full_name=user.full_name,
                role=user.role,
                school_id=user.school_id,
                school_name=school_name,
                modules_total=total,
                modules_completed=completed,
                modules_in_progress=in_progress,
                addon_modules=int(addon_modules or 0),
                status=user_status,
                progress_percent=round(completed / total * 100) if total else 0,
                last_activity_at=last_activity_at,
            )
        )

    summary = OnboardingReportSummaryOut(
        total_users=len(items),
        users_not_started=sum(1 for item in items if item.status == "not_started"),
        users_in_progress=sum(1 for item in items if item.status == "in_progress"),
        users_completed=sum(1 for item in items if item.status == "completed"),
        modules_total=sum(item.modules_total for item in items),
        modules_completed=sum(item.modules_completed for item in items),
        modules_in_progress=sum(item.modules_in_progress for item in items),
        addon_modules=sum(item.addon_modules for item in items),
        progress_percent=(
            round(
                sum(item.modules_completed for item in items)
                / sum(item.modules_total for item in items)
                * 100
            )
            if sum(item.modules_total for item in items)
            else 0
        ),
        by_role=dict(Counter(item.role for item in items)),
    )
    total = len(items)
    return items[offset : offset + limit], summary, total


@router.get(
    "/reports/summary",
    response_model=OnboardingReportSummaryOut,
    summary="Сводка прохождения обучения",
    dependencies=REPORT_DEPS,
)
async def report_summary(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=120),
) -> OnboardingReportSummaryOut:
    _items, summary, _total = await _report_data(
        session,
        current_user,
        school_id=school_id,
        role=role,
        status_filter=status_filter,
        search=search,
        limit=1,
        offset=0,
    )
    return summary


@router.get(
    "/reports/users",
    response_model=OnboardingReportUsersOut,
    summary="Прогресс обучения пользователей",
    dependencies=REPORT_DEPS,
)
async def report_users(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> OnboardingReportUsersOut:
    items, summary, total = await _report_data(
        session,
        current_user,
        school_id=school_id,
        role=role,
        status_filter=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return OnboardingReportUsersOut(
        items=items, total=total, limit=limit, offset=offset, summary=summary
    )


@router.get(
    "/reports/export.csv",
    summary="Выгрузка прогресса обучения",
    dependencies=REPORT_DEPS,
)
async def export_report(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=120),
) -> Response:
    items, _summary, _total = await _report_data(
        session,
        current_user,
        school_id=school_id,
        role=role,
        status_filter=status_filter,
        search=search,
        limit=100000,
        offset=0,
    )
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "Логин",
            "ФИО",
            "Роль",
            "Школа",
            "Модулей всего",
            "Завершено",
            "В процессе",
            "Дообучение",
            "Статус",
            "Прогресс, %",
            "Последняя активность",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.login,
                item.full_name,
                item.role,
                item.school_name or "",
                item.modules_total,
                item.modules_completed,
                item.modules_in_progress,
                item.addon_modules,
                item.status,
                item.progress_percent,
                item.last_activity_at.isoformat() if item.last_activity_at else "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="onboarding-progress.csv"'
        },
    )


@router.post(
    "/reports/users/{user_id}/reset",
    response_model=Message,
    summary="Сбросить прогресс обучения пользователя",
    dependencies=MANAGE_DEPS,
)
async def reset_report_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> Message:
    target = await session.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == "teacher":
        student_ids = await _teacher_student_ids(session, current_user.id)
        allowed = target.id in student_ids
    elif current_user.role == "parent":
        child_ids = await _parent_child_ids(session, current_user.id)
        allowed = target.id in child_ids
    else:
        school_ids = await _managed_school_ids(session, current_user)
        allowed = school_ids is None or (
            target.school_id is not None and target.school_id in school_ids
        )
    if not allowed:
        raise HTTPException(status_code=403, detail="User is outside the report scope")

    count = await reset_user_modules(session, target.id)
    add_audit_event(
        session,
        action="onboarding_progress_reset",
        entity_type="user",
        entity_id=target.id,
        school_id=target.school_id,
        user_id=current_user.id,
        details={"modules": count, "target_login": target.login},
    )
    await session.commit()
    return Message(status="ok", detail=f"Сброшено модулей: {count}")
