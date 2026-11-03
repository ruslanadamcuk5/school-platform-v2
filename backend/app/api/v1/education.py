"""Education level APIs for primary, secondary, vocational and higher education.

Each level is a separately activatable service.  The routers share one
implementation because the core contract is identical: an institution offers a
level, groups belong to the level, and professional levels add programmes and
academic profiles.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUser,
    SessionDep,
    ensure_school_access,
    require_permission,
    require_service,
)
from app.core.config import settings
from app.core.education import (
    INSTITUTION_TYPE_LABELS,
    LEVEL_INFO,
    LEVEL_LABELS,
    PROFESSIONAL_LEVELS,
    EducationLevelInfo,
)
from app.models.education import (
    EducationProgram,
    StaffAcademicProfile,
    StudentAcademicProfile,
)
from app.models.iam import User
from app.models.org import ClassMembership, School, SchoolClass
from app.schemas.education import (
    EducationGroupOut,
    EducationLevelOut,
    EducationOverviewOut,
    EducationProgramCreate,
    EducationProgramOut,
    EducationProgramUpdate,
    EducationTotalsOut,
    StaffAcademicProfileCreate,
    StaffAcademicProfileOut,
    StaffAcademicProfileUpdate,
    StudentAcademicProfileCreate,
    StudentAcademicProfileOut,
    StudentAcademicProfileUpdate,
)
from app.services.audit import add_audit_event

router = APIRouter(prefix="/education", tags=["education"])


def _level_or_404(level: str) -> EducationLevelInfo:
    info = LEVEL_INFO.get(level)
    if info is None:
        raise HTTPException(status_code=404, detail="Unknown education level")
    return info


def _level_out(info: EducationLevelInfo) -> EducationLevelOut:
    return EducationLevelOut(**info.payload)


async def _school_for_level(
    session: AsyncSession,
    current_user: User,
    school_id: uuid.UUID | None,
    level: str,
) -> School:
    tenant_id = ensure_school_access(current_user, school_id)
    school = await session.get(School, tenant_id)
    if school is None or school.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Institution not found")
    levels = [item for item in (school.education_levels or []) if item]
    if level not in levels:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Institution does not provide the '{level}' education level"
            ),
        )
    return school


async def _available_years(
    session: AsyncSession, school_id: uuid.UUID, level: str
) -> list[str]:
    rows = (
        await session.execute(
            select(SchoolClass.academic_year)
            .where(
                SchoolClass.school_id == school_id,
                SchoolClass.education_level == level,
                SchoolClass.deleted_at.is_(None),
            )
            .distinct()
            .order_by(SchoolClass.academic_year.desc())
        )
    ).scalars().all()
    return [year for year in rows if year]


async def _group_query(
    session: AsyncSession,
    school_id: uuid.UUID,
    level: str,
    academic_year: str,
) -> list[SchoolClass]:
    rows = (
        await session.execute(
            select(SchoolClass)
            .where(
                SchoolClass.school_id == school_id,
                SchoolClass.education_level == level,
                SchoolClass.academic_year == academic_year,
                SchoolClass.deleted_at.is_(None),
            )
            .options(selectinload(SchoolClass.homeroom_teacher))
            .order_by(SchoolClass.grade, SchoolClass.letter)
        )
    ).scalars().all()
    return list(rows)


async def _students_by_group(
    session: AsyncSession, group_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not group_ids:
        return {}
    rows = (
        await session.execute(
            select(ClassMembership.class_id, func.count())
            .where(
                ClassMembership.class_id.in_(group_ids),
                ClassMembership.left_at.is_(None),
                ClassMembership.role_in_class == "student",
            )
            .group_by(ClassMembership.class_id)
        )
    ).all()
    return {class_id: count for class_id, count in rows}


def _group_out(
    school_class: SchoolClass,
    students: int,
    program_name: str | None,
) -> EducationGroupOut:
    return EducationGroupOut(
        id=school_class.id,
        name=school_class.display_name,
        grade=school_class.grade,
        letter=school_class.letter,
        education_level=school_class.education_level,  # type: ignore[arg-type]
        course_year=school_class.course_year,
        program_id=school_class.program_id,
        program_name=program_name,
        academic_year=school_class.academic_year,
        students=students,
        curator_name=(
            school_class.homeroom_teacher.full_name
            if school_class.homeroom_teacher
            else None
        ),
        is_active=school_class.is_active,
    )


async def _program_map(
    session: AsyncSession,
    school_id: uuid.UUID,
    level: str,
) -> dict[uuid.UUID, EducationProgram]:
    rows = (
        await session.execute(
            select(EducationProgram).where(
                EducationProgram.institution_id == school_id,
                EducationProgram.education_level == level,
                EducationProgram.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    return {program.id: program for program in rows}


async def _overview(
    session: AsyncSession,
    current_user: User,
    school_id: uuid.UUID | None,
    level: str,
    academic_year: str | None,
) -> EducationOverviewOut:
    info = _level_or_404(level)
    school = await _school_for_level(session, current_user, school_id, level)
    available_years = await _available_years(session, school.id, level)
    year = academic_year or (
        available_years[0] if available_years else settings.seed_academic_year
    )
    groups = await _group_query(session, school.id, level, year)
    group_ids = [group.id for group in groups]
    students_by_group = await _students_by_group(session, group_ids)
    programs = list(
        (
            await session.execute(
                select(EducationProgram)
                .where(
                    EducationProgram.institution_id == school.id,
                    EducationProgram.education_level == level,
                    EducationProgram.deleted_at.is_(None),
                )
                .order_by(EducationProgram.name)
            )
        ).scalars().all()
    )
    program_names = {program.id: program.name for program in programs}

    student_total = 0
    if group_ids:
        student_total = int(
            (
                await session.execute(
                    select(func.count(func.distinct(ClassMembership.user_id)))
                    .where(
                        ClassMembership.class_id.in_(group_ids),
                        ClassMembership.left_at.is_(None),
                        ClassMembership.role_in_class == "student",
                    )
                )
            ).scalar_one()
            or 0
        )
    teacher_total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.school_id == school.id,
                    User.role == "teacher",
                    User.deleted_at.is_(None),
                    User.is_active.is_(True),
                )
            )
        ).scalar_one()
        or 0
    )
    if info.is_professional:
        student_profiles_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(StudentAcademicProfile)
                    .where(
                        StudentAcademicProfile.institution_id == school.id,
                        StudentAcademicProfile.academic_status == "active",
                    )
                )
            ).scalar_one()
            or 0
        )
    else:
        student_profiles_count = 0
    staff_profiles_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StaffAcademicProfile)
                .where(StaffAcademicProfile.institution_id == school.id)
            )
        ).scalar_one()
        or 0
    )

    return EducationOverviewOut(
        institution_id=school.id,
        institution_name=school.name,
        institution_type=school.institution_type,
        institution_type_label=INSTITUTION_TYPE_LABELS.get(
            school.institution_type, school.institution_type
        ),
        education_levels=list(school.education_levels or []),
        level=_level_out(info),
        academic_year=year,
        available_years=available_years,
        generated_at=datetime.now(timezone.utc),
        totals=EducationTotalsOut(
            students=student_total or student_profiles_count,
            teachers=teacher_total,
            groups=len(groups),
            programs=len(programs),
        ),
        groups=[
            _group_out(
                group,
                students_by_group.get(group.id, 0),
                program_names.get(group.program_id) if group.program_id else None,
            )
            for group in groups
        ],
        programs=[
            EducationProgramOut.model_validate(program) for program in programs
        ],
        student_profiles_count=student_profiles_count,
        staff_profiles_count=staff_profiles_count,
    )


async def _program_for_institution(
    session: AsyncSession,
    program_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> EducationProgram:
    program = await session.get(EducationProgram, program_id)
    if (
        program is None
        or program.deleted_at is not None
        or program.institution_id != school_id
        or program.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Education program not found")
    return program


async def _group_for_institution(
    session: AsyncSession,
    group_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> SchoolClass:
    group = await session.get(SchoolClass, group_id)
    if (
        group is None
        or group.deleted_at is not None
        or group.school_id != school_id
        or group.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Academic group not found")
    return group


def _student_profile_out(profile: StudentAcademicProfile) -> StudentAcademicProfileOut:
    return StudentAcademicProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        login=profile.user.login,
        full_name=profile.user.full_name,
        institution_id=profile.institution_id,
        program_id=profile.program_id,
        program_name=profile.program.name if profile.program else None,
        group_id=profile.group_id,
        group_name=profile.group.display_name if profile.group else None,
        course_year=profile.course_year,
        record_book_number=profile.record_book_number,
        funding_type=profile.funding_type,
        enrollment_year=profile.enrollment_year,
        academic_status=profile.academic_status,
        profile=profile.profile or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _staff_profile_out(profile: StaffAcademicProfile) -> StaffAcademicProfileOut:
    return StaffAcademicProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        login=profile.user.login,
        full_name=profile.user.full_name,
        institution_id=profile.institution_id,
        department=profile.department,
        position=profile.position,
        academic_degree=profile.academic_degree,
        academic_title=profile.academic_title,
        profile=profile.profile or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _build_level_router(level: str) -> APIRouter:
    info = _level_or_404(level)
    professional = level in PROFESSIONAL_LEVELS
    level_router = APIRouter(
        prefix=f"/education/{level}",
        tags=["education", LEVEL_LABELS[level]],
        dependencies=[Depends(require_service(info.service_code))],
    )
    read_dep = require_permission(info.read_permission)
    program_dep = (
        require_permission(info.program_permission)
        if info.program_permission
        else None
    )
    profile_read_dep = (
        require_permission(info.profile_read_permission)
        if info.profile_read_permission
        else None
    )
    profile_manage_dep = (
        require_permission(info.profile_manage_permission)
        if info.profile_manage_permission
        else None
    )

    @level_router.get(
        "/overview",
        response_model=EducationOverviewOut,
        summary=f"Сводка ступени: {LEVEL_LABELS[level]}",
    )
    async def overview(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        academic_year: str | None = Query(
            default=None, pattern=r"^\d{4}/\d{4}$"
        ),
        _: User = Depends(read_dep),
    ):
        return await _overview(
            session, current_user, school_id, level, academic_year
        )

    @level_router.get(
        "/groups",
        response_model=list[EducationGroupOut],
        summary="Учебные группы и классы ступени",
    )
    async def list_groups(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        academic_year: str | None = Query(
            default=None, pattern=r"^\d{4}/\d{4}$"
        ),
        _: User = Depends(read_dep),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        years = await _available_years(session, school.id, level)
        year = academic_year or (
            years[0] if years else settings.seed_academic_year
        )
        groups = await _group_query(session, school.id, level, year)
        counts = await _students_by_group(session, [item.id for item in groups])
        programs = await _program_map(session, school.id, level)
        return [
            _group_out(
                group,
                counts.get(group.id, 0),
                programs[group.program_id].name if group.program_id in programs else None,
            )
            for group in groups
        ]

    @level_router.get(
        "/programs",
        response_model=list[EducationProgramOut],
        summary="Образовательные программы и специальности",
    )
    async def list_programs(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        _: User = Depends(read_dep),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        if not professional:
            return []
        rows = (
            await session.execute(
                select(EducationProgram)
                .where(
                    EducationProgram.institution_id == school.id,
                    EducationProgram.education_level == level,
                    EducationProgram.deleted_at.is_(None),
                )
                .order_by(EducationProgram.name)
            )
        ).scalars().all()
        return [EducationProgramOut.model_validate(item) for item in rows]

    if program_dep is not None:

        @level_router.post(
            "/programs",
            response_model=EducationProgramOut,
            status_code=201,
            summary="Создать образовательную программу",
        )
        async def create_program(
            payload: EducationProgramCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            exists = (
                await session.execute(
                    select(EducationProgram.id).where(
                        EducationProgram.institution_id == school.id,
                        EducationProgram.code == payload.code,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Program with this code already exists",
                )
            program = EducationProgram(
                institution_id=school.id,
                education_level=level,
                code=payload.code,
                name=payload.name,
                qualification=payload.qualification,
                duration_years=payload.duration_years,
                profile=payload.profile,
                is_active=payload.is_active,
            )
            session.add(program)
            await session.flush()
            add_audit_event(
                session,
                action="education_program_created",
                entity_type="education_program",
                entity_id=program.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"level": level, "code": program.code},
            )
            await session.commit()
            await session.refresh(program)
            return EducationProgramOut.model_validate(program)

        @level_router.patch(
            "/programs/{program_id}",
            response_model=EducationProgramOut,
            summary="Изменить образовательную программу",
        )
        async def update_program(
            program_id: uuid.UUID,
            payload: EducationProgramUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            program = await _program_for_institution(
                session, program_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field, value in updates.items():
                setattr(program, field, value)
            add_audit_event(
                session,
                action="education_program_updated",
                entity_type="education_program",
                entity_id=program.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(program)
            return EducationProgramOut.model_validate(program)

    @level_router.get(
        "/profiles",
        response_model=list[StudentAcademicProfileOut],
        summary="Академические профили обучающихся",
    )
    async def list_profiles(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        academic_status: str | None = Query(default=None),
        _: User = Depends(
            profile_read_dep if profile_read_dep is not None else read_dep
        ),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        if not professional:
            return []
        stmt = (
            select(StudentAcademicProfile)
            .where(StudentAcademicProfile.institution_id == school.id)
            .options(
                selectinload(StudentAcademicProfile.user),
                selectinload(StudentAcademicProfile.program),
                selectinload(StudentAcademicProfile.group),
            )
            .order_by(StudentAcademicProfile.created_at.desc())
        )
        if academic_status:
            stmt = stmt.where(
                StudentAcademicProfile.academic_status == academic_status
            )
        rows = (await session.execute(stmt)).scalars().all()
        return [_student_profile_out(row) for row in rows]

    if profile_manage_dep is not None:

        @level_router.post(
            "/profiles",
            response_model=StudentAcademicProfileOut,
            status_code=201,
            summary="Создать академический профиль обучающегося",
        )
        async def create_profile(
            payload: StudentAcademicProfileCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(profile_manage_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            user = await session.get(User, payload.user_id)
            if (
                user is None
                or user.deleted_at is not None
                or user.school_id != school.id
            ):
                raise HTTPException(
                    status_code=400,
                    detail="User must belong to the same institution",
                )
            if payload.program_id is not None:
                await _program_for_institution(
                    session, payload.program_id, school.id, level
                )
            if payload.group_id is not None:
                await _group_for_institution(
                    session, payload.group_id, school.id, level
                )
            exists = (
                await session.execute(
                    select(StudentAcademicProfile.id).where(
                        StudentAcademicProfile.user_id == user.id
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Academic profile for this user already exists",
                )
            profile = StudentAcademicProfile(
                user_id=user.id,
                institution_id=school.id,
                program_id=payload.program_id,
                group_id=payload.group_id,
                course_year=payload.course_year,
                record_book_number=payload.record_book_number,
                funding_type=payload.funding_type,
                enrollment_year=payload.enrollment_year,
                academic_status=payload.academic_status,
                profile=payload.profile,
            )
            session.add(profile)
            await session.flush()
            add_audit_event(
                session,
                action="student_academic_profile_created",
                entity_type="student_academic_profile",
                entity_id=profile.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "student_id": str(user.id)},
            )
            await session.commit()
            stmt = (
                select(StudentAcademicProfile)
                .where(StudentAcademicProfile.id == profile.id)
                .options(
                    selectinload(StudentAcademicProfile.user),
                    selectinload(StudentAcademicProfile.program),
                    selectinload(StudentAcademicProfile.group),
                )
            )
            saved = (await session.execute(stmt)).scalar_one()
            return _student_profile_out(saved)

        @level_router.patch(
            "/profiles/{profile_id}",
            response_model=StudentAcademicProfileOut,
            summary="Изменить академический профиль обучающегося",
        )
        async def update_profile(
            profile_id: uuid.UUID,
            payload: StudentAcademicProfileUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(profile_manage_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            profile = await session.get(StudentAcademicProfile, profile_id)
            if profile is None or profile.institution_id != school.id:
                raise HTTPException(
                    status_code=404, detail="Academic profile not found"
                )
            updates = payload.model_dump(exclude_unset=True)
            if updates.get("program_id") is not None:
                await _program_for_institution(
                    session, updates["program_id"], school.id, level
                )
            if updates.get("group_id") is not None:
                await _group_for_institution(
                    session, updates["group_id"], school.id, level
                )
            for field, value in updates.items():
                setattr(profile, field, value)
            add_audit_event(
                session,
                action="student_academic_profile_updated",
                entity_type="student_academic_profile",
                entity_id=profile.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            stmt = (
                select(StudentAcademicProfile)
                .where(StudentAcademicProfile.id == profile.id)
                .options(
                    selectinload(StudentAcademicProfile.user),
                    selectinload(StudentAcademicProfile.program),
                    selectinload(StudentAcademicProfile.group),
                )
            )
            saved = (await session.execute(stmt)).scalar_one()
            return _student_profile_out(saved)

    @level_router.get(
        "/staff-profiles",
        response_model=list[StaffAcademicProfileOut],
        summary="Академические профили преподавателей",
    )
    async def list_staff_profiles(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        _: User = Depends(
            profile_read_dep if profile_read_dep is not None else read_dep
        ),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        if not professional:
            return []
        rows = (
            await session.execute(
                select(StaffAcademicProfile)
                .where(StaffAcademicProfile.institution_id == school.id)
                .options(selectinload(StaffAcademicProfile.user))
                .order_by(StaffAcademicProfile.created_at.desc())
            )
        ).scalars().all()
        return [_staff_profile_out(row) for row in rows]

    if profile_manage_dep is not None:

        @level_router.post(
            "/staff-profiles",
            response_model=StaffAcademicProfileOut,
            status_code=201,
            summary="Создать академический профиль преподавателя",
        )
        async def create_staff_profile(
            payload: StaffAcademicProfileCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(profile_manage_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            user = await session.get(User, payload.user_id)
            if (
                user is None
                or user.deleted_at is not None
                or user.school_id != school.id
            ):
                raise HTTPException(
                    status_code=400,
                    detail="User must belong to the same institution",
                )
            exists = (
                await session.execute(
                    select(StaffAcademicProfile.id).where(
                        StaffAcademicProfile.user_id == user.id
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Staff academic profile already exists",
                )
            profile = StaffAcademicProfile(
                user_id=user.id,
                institution_id=school.id,
                department=payload.department,
                position=payload.position,
                academic_degree=payload.academic_degree,
                academic_title=payload.academic_title,
                profile=payload.profile,
            )
            session.add(profile)
            await session.flush()
            add_audit_event(
                session,
                action="staff_academic_profile_created",
                entity_type="staff_academic_profile",
                entity_id=profile.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "staff_id": str(user.id)},
            )
            await session.commit()
            stmt = (
                select(StaffAcademicProfile)
                .where(StaffAcademicProfile.id == profile.id)
                .options(selectinload(StaffAcademicProfile.user))
            )
            saved = (await session.execute(stmt)).scalar_one()
            return _staff_profile_out(saved)

        @level_router.patch(
            "/staff-profiles/{profile_id}",
            response_model=StaffAcademicProfileOut,
            summary="Изменить академический профиль преподавателя",
        )
        async def update_staff_profile(
            profile_id: uuid.UUID,
            payload: StaffAcademicProfileUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(profile_manage_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            profile = await session.get(StaffAcademicProfile, profile_id)
            if profile is None or profile.institution_id != school.id:
                raise HTTPException(
                    status_code=404, detail="Staff academic profile not found"
                )
            updates = payload.model_dump(exclude_unset=True)
            for field, value in updates.items():
                setattr(profile, field, value)
            add_audit_event(
                session,
                action="staff_academic_profile_updated",
                entity_type="staff_academic_profile",
                entity_id=profile.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            stmt = (
                select(StaffAcademicProfile)
                .where(StaffAcademicProfile.id == profile.id)
                .options(selectinload(StaffAcademicProfile.user))
            )
            saved = (await session.execute(stmt)).scalar_one()
            return _staff_profile_out(saved)

    return level_router


primary_router = _build_level_router("primary")
secondary_router = _build_level_router("secondary")
vocational_router = _build_level_router("vocational")
higher_router = _build_level_router("higher")

# Keep a reference for documentation and tests; it is not mounted directly.
LEVEL_ROUTERS = (
    primary_router,
    secondary_router,
    vocational_router,
    higher_router,
)
