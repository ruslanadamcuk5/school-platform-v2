"""Education level APIs for primary, secondary, vocational and higher education.

Each level is a separately activatable service.  The routers share one
implementation because the core contract is identical: an institution offers a
level, groups belong to the level, and professional levels add programmes and
academic profiles.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
    AcademicSession,
    CreditTransfer,
    CurriculumComponent,
    EducationCurriculum,
    EducationProgram,
    SessionStatement,
    StaffAcademicProfile,
    StatementRecord,
    StudentAcademicProfile,
)
from app.models.iam import User
from app.models.org import ClassMembership, School, SchoolClass
from app.schemas.education import (
    AcademicSessionCreate,
    AcademicSessionOut,
    AcademicSessionUpdate,
    CreditTransferCreate,
    CreditTransferOut,
    CreditTransferUpdate,
    CurriculumComponentCreate,
    CurriculumComponentOut,
    CurriculumComponentUpdate,
    EducationCurriculumCreate,
    EducationCurriculumOut,
    EducationCurriculumUpdate,
    EducationGroupOut,
    EducationLevelOut,
    EducationOverviewOut,
    EducationProgramCreate,
    EducationProgramOut,
    EducationProgramUpdate,
    EducationTotalsOut,
    SessionStatementCreate,
    SessionStatementOut,
    SessionStatementUpdate,
    StaffAcademicProfileCreate,
    StaffAcademicProfileOut,
    StaffAcademicProfileUpdate,
    StatementRecordBulk,
    StatementRecordOut,
    StudentAcademicProfileCreate,
    StudentAcademicProfileOut,
    StudentAcademicProfileUpdate,
    TranscriptItemOut,
    TranscriptOut,
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


def _curriculum_out(curriculum: EducationCurriculum) -> EducationCurriculumOut:
    components = [
        CurriculumComponentOut.model_validate(item)
        for item in sorted(
            curriculum.components,
            key=lambda item: (item.order_index, item.semester, item.code),
        )
    ]
    return EducationCurriculumOut(
        id=curriculum.id,
        institution_id=curriculum.institution_id,
        program_id=curriculum.program_id,
        program_name=curriculum.program.name if curriculum.program else "",
        education_level=curriculum.education_level,  # type: ignore[arg-type]
        academic_year=curriculum.academic_year,
        name=curriculum.name,
        description=curriculum.description,
        status=curriculum.status,  # type: ignore[arg-type]
        approved_at=curriculum.approved_at,
        approved_by_id=curriculum.approved_by_id,
        profile=curriculum.profile or {},
        total_credits=round(sum(item.credits for item in components), 2),
        components=components,
        created_at=curriculum.created_at,
        updated_at=curriculum.updated_at,
    )


async def _curriculum_for_institution(
    session: AsyncSession,
    curriculum_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> EducationCurriculum:
    curriculum = (
        await session.execute(
            select(EducationCurriculum)
            .where(EducationCurriculum.id == curriculum_id)
            .options(
                selectinload(EducationCurriculum.program),
                selectinload(EducationCurriculum.components),
            )
        )
    ).scalar_one_or_none()
    if (
        curriculum is None
        or curriculum.institution_id != school_id
        or curriculum.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Curriculum not found")
    return curriculum


async def _component_for_curriculum(
    session: AsyncSession,
    component_id: uuid.UUID,
    curriculum_id: uuid.UUID,
) -> CurriculumComponent:
    component = await session.get(CurriculumComponent, component_id)
    if component is None or component.curriculum_id != curriculum_id:
        raise HTTPException(status_code=404, detail="Curriculum component not found")
    return component


def _ensure_component_hours(
    academic_hours: int, contact_hours: int
) -> None:
    if contact_hours > academic_hours:
        raise HTTPException(
            status_code=422,
            detail="contact_hours cannot exceed academic_hours",
        )


def _session_out(item: AcademicSession) -> AcademicSessionOut:
    return AcademicSessionOut.model_validate(item)


def _statement_record_out(record: StatementRecord) -> StatementRecordOut:
    return StatementRecordOut(
        id=record.id,
        statement_id=record.statement_id,
        student_id=record.student_id,
        student_login=record.student.login if record.student else "",
        student_name=record.student.full_name if record.student else "",
        grade=record.grade,
        result=record.result,  # type: ignore[arg-type]
        credits_awarded=float(record.credits_awarded or 0),
        comment=record.comment,
        profile=record.profile or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _statement_out(statement: SessionStatement) -> SessionStatementOut:
    records = sorted(
        statement.records,
        key=lambda item: (
            item.student.full_name if item.student else "",
            item.student_id,
        ),
    )
    return SessionStatementOut(
        id=statement.id,
        session_id=statement.session_id,
        institution_id=statement.institution_id,
        education_level=statement.education_level,  # type: ignore[arg-type]
        group_id=statement.group_id,
        group_name=statement.group.display_name if statement.group else "",
        curriculum_id=statement.curriculum_id,
        curriculum_name=statement.curriculum.name if statement.curriculum else "",
        component_id=statement.component_id,
        component_code=statement.component.code if statement.component else "",
        component_name=statement.component.name if statement.component else "",
        component_type=(
            statement.component.component_type  # type: ignore[arg-type]
            if statement.component
            else "other"
        ),
        semester=statement.component.semester if statement.component else 0,
        component_credits=(
            float(statement.component.credits) if statement.component else 0
        ),
        teacher_id=statement.teacher_id,
        teacher_name=statement.teacher.full_name if statement.teacher else None,
        statement_number=statement.statement_number,
        issued_on=statement.issued_on,
        status=statement.status,  # type: ignore[arg-type]
        approved_at=statement.approved_at,
        approved_by_id=statement.approved_by_id,
        notes=statement.notes,
        profile=statement.profile or {},
        records=[_statement_record_out(record) for record in records],
        created_at=statement.created_at,
        updated_at=statement.updated_at,
    )


def _credit_transfer_out(item: CreditTransfer) -> CreditTransferOut:
    return CreditTransferOut(
        id=item.id,
        institution_id=item.institution_id,
        education_level=item.education_level,  # type: ignore[arg-type]
        student_id=item.student_id,
        student_login=item.student.login if item.student else "",
        student_name=item.student.full_name if item.student else "",
        target_program_id=item.target_program_id,
        target_program_name=(
            item.target_program.name if item.target_program else None
        ),
        target_component_id=item.target_component_id,
        target_component_code=(
            item.target_component.code if item.target_component else None
        ),
        target_component_name=(
            item.target_component.name if item.target_component else None
        ),
        source_institution=item.source_institution,
        source_program=item.source_program,
        source_component_code=item.source_component_code,
        source_component_name=item.source_component_name,
        source_academic_year=item.source_academic_year,
        source_credits=float(item.source_credits or 0),
        awarded_credits=float(item.awarded_credits or 0),
        source_grade=item.source_grade,
        document_number=item.document_number,
        reason=item.reason,
        status=item.status,  # type: ignore[arg-type]
        decided_at=item.decided_at,
        decided_by_id=item.decided_by_id,
        profile=item.profile or {},
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _session_for_institution(
    session: AsyncSession,
    session_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> AcademicSession:
    item = await session.get(AcademicSession, session_id)
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Academic session not found")
    return item


async def _statement_for_institution(
    session: AsyncSession,
    statement_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> SessionStatement:
    item = (
        await session.execute(
            select(SessionStatement)
            .where(SessionStatement.id == statement_id)
            .options(
                selectinload(SessionStatement.group),
                selectinload(SessionStatement.curriculum),
                selectinload(SessionStatement.component),
                selectinload(SessionStatement.teacher),
                selectinload(SessionStatement.records).selectinload(
                    StatementRecord.student
                ),
            )
        )
    ).scalar_one_or_none()
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Academic statement not found")
    return item


async def _credit_transfer_for_institution(
    session: AsyncSession,
    transfer_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> CreditTransfer:
    item = (
        await session.execute(
            select(CreditTransfer)
            .where(CreditTransfer.id == transfer_id)
            .options(
                selectinload(CreditTransfer.student),
                selectinload(CreditTransfer.target_program),
                selectinload(CreditTransfer.target_component),
            )
        )
    ).scalar_one_or_none()
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Credit transfer not found")
    return item


async def _student_profile_for_institution(
    session: AsyncSession,
    profile_id: uuid.UUID,
    school_id: uuid.UUID,
) -> StudentAcademicProfile:
    item = (
        await session.execute(
            select(StudentAcademicProfile)
            .where(StudentAcademicProfile.id == profile_id)
            .options(
                selectinload(StudentAcademicProfile.user),
                selectinload(StudentAcademicProfile.program),
                selectinload(StudentAcademicProfile.group),
            )
        )
    ).scalar_one_or_none()
    if item is None or item.institution_id != school_id:
        raise HTTPException(
            status_code=404, detail="Student academic profile not found"
        )
    return item


async def _component_for_institution(
    session: AsyncSession,
    component_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> CurriculumComponent:
    item = (
        await session.execute(
            select(CurriculumComponent)
            .join(
                EducationCurriculum,
                CurriculumComponent.curriculum_id == EducationCurriculum.id,
            )
            .where(
                CurriculumComponent.id == component_id,
                EducationCurriculum.institution_id == school_id,
                EducationCurriculum.education_level == level,
            )
            .options(selectinload(CurriculumComponent.curriculum))
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=404, detail="Curriculum component not found"
        )
    return item


async def _user_for_institution(
    session: AsyncSession,
    user_id: uuid.UUID,
    school_id: uuid.UUID,
    allowed_roles: set[str] | None = None,
) -> User:
    user = await session.get(User, user_id)
    if (
        user is None
        or user.deleted_at is not None
        or user.school_id != school_id
    ):
        raise HTTPException(
            status_code=400,
            detail="User must belong to the same institution",
        )
    if allowed_roles is not None and user.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="User role is not allowed")
    return user


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
        "/curricula",
        response_model=list[EducationCurriculumOut],
        summary="Учебные планы профессиональной ступени",
    )
    async def list_curricula(
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        program_id: uuid.UUID | None = Query(default=None),
        academic_year: str | None = Query(
            default=None, pattern=r"^\d{4}/\d{4}$"
        ),
        status: str | None = Query(default=None),
        _: User = Depends(read_dep),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        if not professional:
            return []
        if status is not None and status not in (
            "draft",
            "approved",
            "archived",
        ):
            raise HTTPException(status_code=422, detail="Unknown curriculum status")
        stmt = (
            select(EducationCurriculum)
            .where(
                EducationCurriculum.institution_id == school.id,
                EducationCurriculum.education_level == level,
            )
            .options(
                selectinload(EducationCurriculum.program),
                selectinload(EducationCurriculum.components),
            )
            .order_by(
                EducationCurriculum.academic_year.desc(),
                EducationCurriculum.name,
            )
        )
        if program_id is not None:
            stmt = stmt.where(EducationCurriculum.program_id == program_id)
        if academic_year is not None:
            stmt = stmt.where(
                EducationCurriculum.academic_year == academic_year
            )
        if status is not None:
            stmt = stmt.where(EducationCurriculum.status == status)
        rows = (await session.execute(stmt)).scalars().all()
        return [_curriculum_out(item) for item in rows]

    @level_router.get(
        "/curricula/{curriculum_id}",
        response_model=EducationCurriculumOut,
        summary="Учебный план с компонентами",
    )
    async def get_curriculum(
        curriculum_id: uuid.UUID,
        current_user: CurrentUser,
        session: SessionDep,
        school_id: uuid.UUID | None = Query(default=None),
        _: User = Depends(read_dep),
    ):
        school = await _school_for_level(session, current_user, school_id, level)
        if not professional:
            raise HTTPException(status_code=404, detail="Curriculum not found")
        curriculum = await _curriculum_for_institution(
            session, curriculum_id, school.id, level
        )
        return _curriculum_out(curriculum)

    if program_dep is not None:

        @level_router.post(
            "/curricula",
            response_model=EducationCurriculumOut,
            status_code=201,
            summary="Создать учебный план",
        )
        async def create_curriculum(
            payload: EducationCurriculumCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            await _program_for_institution(
                session, payload.program_id, school.id, level
            )
            exists = (
                await session.execute(
                    select(EducationCurriculum.id).where(
                        EducationCurriculum.program_id == payload.program_id,
                        EducationCurriculum.academic_year
                        == payload.academic_year,
                        EducationCurriculum.name == payload.name,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Curriculum with this name and year already exists",
                )
            approved = payload.status == "approved"
            curriculum = EducationCurriculum(
                institution_id=school.id,
                program_id=payload.program_id,
                education_level=level,
                academic_year=payload.academic_year,
                name=payload.name,
                description=payload.description,
                status=payload.status,
                approved_at=datetime.now(timezone.utc) if approved else None,
                approved_by_id=current_user.id if approved else None,
                profile=payload.profile,
            )
            session.add(curriculum)
            await session.flush()
            add_audit_event(
                session,
                action="education_curriculum_created",
                entity_type="education_curriculum",
                entity_id=curriculum.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "program_id": str(payload.program_id),
                    "academic_year": payload.academic_year,
                },
            )
            await session.commit()
            saved = await _curriculum_for_institution(
                session, curriculum.id, school.id, level
            )
            return _curriculum_out(saved)

        @level_router.patch(
            "/curricula/{curriculum_id}",
            response_model=EducationCurriculumOut,
            summary="Изменить учебный план",
        )
        async def update_curriculum(
            curriculum_id: uuid.UUID,
            payload: EducationCurriculumUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            curriculum = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            new_name = updates.get("name")
            if new_name is not None and new_name != curriculum.name:
                exists = (
                    await session.execute(
                        select(EducationCurriculum.id).where(
                            EducationCurriculum.program_id
                            == curriculum.program_id,
                            EducationCurriculum.academic_year
                            == curriculum.academic_year,
                            EducationCurriculum.name == new_name,
                            EducationCurriculum.id != curriculum.id,
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Curriculum with this name and year already exists"
                        ),
                    )
            if "status" in updates:
                if updates["status"] == "approved":
                    curriculum.approved_at = datetime.now(timezone.utc)
                    curriculum.approved_by_id = current_user.id
                else:
                    curriculum.approved_at = None
                    curriculum.approved_by_id = None
            for field, value in updates.items():
                setattr(curriculum, field, value)
            add_audit_event(
                session,
                action="education_curriculum_updated",
                entity_type="education_curriculum",
                entity_id=curriculum.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            saved = await _curriculum_for_institution(
                session, curriculum.id, school.id, level
            )
            return _curriculum_out(saved)

        @level_router.post(
            "/curricula/{curriculum_id}/components",
            response_model=CurriculumComponentOut,
            status_code=201,
            summary="Добавить дисциплину, модуль или практику",
        )
        async def create_curriculum_component(
            curriculum_id: uuid.UUID,
            payload: CurriculumComponentCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            curriculum = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            if curriculum.status == "archived":
                raise HTTPException(
                    status_code=409, detail="Curriculum is archived"
                )
            _ensure_component_hours(
                payload.academic_hours, payload.contact_hours
            )
            exists = (
                await session.execute(
                    select(CurriculumComponent.id).where(
                        CurriculumComponent.curriculum_id == curriculum.id,
                        CurriculumComponent.code == payload.code,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Component with this code already exists",
                )
            component = CurriculumComponent(
                curriculum_id=curriculum.id,
                code=payload.code,
                name=payload.name,
                component_type=payload.component_type,
                semester=payload.semester,
                credits=payload.credits,
                academic_hours=payload.academic_hours,
                contact_hours=payload.contact_hours,
                assessment_type=payload.assessment_type,
                is_optional=payload.is_optional,
                order_index=payload.order_index,
                description=payload.description,
                details=payload.details,
            )
            session.add(component)
            await session.flush()
            add_audit_event(
                session,
                action="curriculum_component_created",
                entity_type="curriculum_component",
                entity_id=component.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "curriculum_id": str(curriculum.id),
                    "component_type": payload.component_type,
                },
            )
            await session.commit()
            await session.refresh(component)
            return CurriculumComponentOut.model_validate(component)

        @level_router.patch(
            "/curricula/{curriculum_id}/components/{component_id}",
            response_model=CurriculumComponentOut,
            summary="Изменить компонент учебного плана",
        )
        async def update_curriculum_component(
            curriculum_id: uuid.UUID,
            component_id: uuid.UUID,
            payload: CurriculumComponentUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            curriculum = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            component = await _component_for_curriculum(
                session, component_id, curriculum.id
            )
            updates = payload.model_dump(exclude_unset=True)
            new_code = updates.get("code")
            if new_code is not None and new_code != component.code:
                exists = (
                    await session.execute(
                        select(CurriculumComponent.id).where(
                            CurriculumComponent.curriculum_id
                            == curriculum.id,
                            CurriculumComponent.code == new_code,
                            CurriculumComponent.id != component.id,
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Component with this code already exists",
                    )
            _ensure_component_hours(
                updates.get("academic_hours", component.academic_hours),
                updates.get("contact_hours", component.contact_hours),
            )
            for field, value in updates.items():
                setattr(component, field, value)
            add_audit_event(
                session,
                action="curriculum_component_updated",
                entity_type="curriculum_component",
                entity_id=component.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(component)
            return CurriculumComponentOut.model_validate(component)

        @level_router.delete(
            "/curricula/{curriculum_id}/components/{component_id}",
            status_code=204,
            summary="Удалить компонент учебного плана",
        )
        async def delete_curriculum_component(
            curriculum_id: uuid.UUID,
            component_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            curriculum = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            component = await _component_for_curriculum(
                session, component_id, curriculum.id
            )
            add_audit_event(
                session,
                action="curriculum_component_deleted",
                entity_type="curriculum_component",
                entity_id=component.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "curriculum_id": str(curriculum.id),
                    "code": component.code,
                },
            )
            await session.delete(component)
            await session.commit()
            return Response(status_code=204)

    if professional and program_dep is not None:

        @level_router.get(
            "/sessions",
            response_model=list[AcademicSessionOut],
            summary="Экзаменационные сессии",
        )
        async def list_sessions(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            academic_year: str | None = Query(
                default=None, pattern=r"^\d{4}/\d{4}$"
            ),
            status: str | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            if status is not None and status not in (
                "planned",
                "active",
                "completed",
                "archived",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown session status"
                )
            stmt = (
                select(AcademicSession)
                .where(
                    AcademicSession.institution_id == school.id,
                    AcademicSession.education_level == level,
                )
                .order_by(
                    AcademicSession.academic_year.desc(),
                    AcademicSession.semester,
                    AcademicSession.name,
                )
            )
            if academic_year is not None:
                stmt = stmt.where(
                    AcademicSession.academic_year == academic_year
                )
            if status is not None:
                stmt = stmt.where(AcademicSession.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            return [_session_out(item) for item in rows]

        @level_router.post(
            "/sessions",
            response_model=AcademicSessionOut,
            status_code=201,
            summary="Создать экзаменационную сессию",
        )
        async def create_session(
            payload: AcademicSessionCreate,
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
                    select(AcademicSession.id).where(
                        AcademicSession.institution_id == school.id,
                        AcademicSession.academic_year == payload.academic_year,
                        AcademicSession.semester == payload.semester,
                        AcademicSession.name == payload.name,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Academic session with this name already exists",
                )
            item = AcademicSession(
                institution_id=school.id,
                education_level=level,
                academic_year=payload.academic_year,
                semester=payload.semester,
                name=payload.name,
                session_type=payload.session_type,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                status=payload.status,
                description=payload.description,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="academic_session_created",
                entity_type="academic_session",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "academic_year": payload.academic_year,
                    "semester": payload.semester,
                },
            )
            await session.commit()
            await session.refresh(item)
            return _session_out(item)

        @level_router.patch(
            "/sessions/{session_id}",
            response_model=AcademicSessionOut,
            summary="Изменить экзаменационную сессию",
        )
        async def update_session(
            session_id: uuid.UUID,
            payload: AcademicSessionUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _session_for_institution(
                session, session_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in (
                "academic_year",
                "semester",
                "name",
                "session_type",
                "status",
                "profile",
            ):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            new_year = updates.get("academic_year", item.academic_year)
            new_semester = updates.get("semester", item.semester)
            new_name = updates.get("name", item.name)
            if (
                new_year != item.academic_year
                or new_semester != item.semester
                or new_name != item.name
            ):
                exists = (
                    await session.execute(
                        select(AcademicSession.id).where(
                            AcademicSession.institution_id == school.id,
                            AcademicSession.academic_year == new_year,
                            AcademicSession.semester == new_semester,
                            AcademicSession.name == new_name,
                            AcademicSession.id != item.id,
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Academic session with this name already exists",
                    )
            starts_on = updates.get("starts_on", item.starts_on)
            ends_on = updates.get("ends_on", item.ends_on)
            if starts_on is not None and ends_on is not None and ends_on < starts_on:
                raise HTTPException(
                    status_code=422,
                    detail="ends_on cannot be earlier than starts_on",
                )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="academic_session_updated",
                entity_type="academic_session",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(item)
            return _session_out(item)

        @level_router.get(
            "/sessions/{session_id}/statements",
            response_model=list[SessionStatementOut],
            summary="Зачётные и экзаменационные ведомости сессии",
        )
        async def list_statements(
            session_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            group_id: uuid.UUID | None = Query(default=None),
            status: str | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            academic_session = await _session_for_institution(
                session, session_id, school.id, level
            )
            if status is not None and status not in (
                "draft",
                "published",
                "approved",
                "archived",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown statement status"
                )
            stmt = (
                select(SessionStatement)
                .where(SessionStatement.session_id == academic_session.id)
                .options(
                    selectinload(SessionStatement.group),
                    selectinload(SessionStatement.curriculum),
                    selectinload(SessionStatement.component),
                    selectinload(SessionStatement.teacher),
                    selectinload(SessionStatement.records).selectinload(
                        StatementRecord.student
                    ),
                )
                .order_by(SessionStatement.statement_number)
            )
            if group_id is not None:
                stmt = stmt.where(SessionStatement.group_id == group_id)
            if status is not None:
                stmt = stmt.where(SessionStatement.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            return [_statement_out(item) for item in rows]

        @level_router.post(
            "/sessions/{session_id}/statements",
            response_model=SessionStatementOut,
            status_code=201,
            summary="Создать зачётную ведомость",
        )
        async def create_statement(
            session_id: uuid.UUID,
            payload: SessionStatementCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            academic_session = await _session_for_institution(
                session, session_id, school.id, level
            )
            group = await _group_for_institution(
                session, payload.group_id, school.id, level
            )
            component = await _component_for_institution(
                session, payload.component_id, school.id, level
            )
            if (
                group.program_id is not None
                and component.curriculum.program_id != group.program_id
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Component belongs to another education program",
                )
            if payload.teacher_id is not None:
                await _user_for_institution(
                    session,
                    payload.teacher_id,
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            exists = (
                await session.execute(
                    select(SessionStatement.id).where(
                        SessionStatement.session_id == academic_session.id,
                        SessionStatement.group_id == group.id,
                        SessionStatement.component_id == component.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Statement for this group and component already exists",
                )
            number_exists = (
                await session.execute(
                    select(SessionStatement.id).where(
                        SessionStatement.institution_id == school.id,
                        SessionStatement.statement_number
                        == payload.statement_number,
                    )
                )
            ).scalar_one_or_none()
            if number_exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Statement with this number already exists",
                )
            item = SessionStatement(
                session_id=academic_session.id,
                institution_id=school.id,
                education_level=level,
                group_id=group.id,
                curriculum_id=component.curriculum_id,
                component_id=component.id,
                teacher_id=payload.teacher_id,
                statement_number=payload.statement_number,
                issued_on=payload.issued_on or date.today(),
                status="draft",
                notes=payload.notes,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="session_statement_created",
                entity_type="session_statement",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "session_id": str(academic_session.id),
                    "group_id": str(group.id),
                    "component_id": str(component.id),
                },
            )
            await session.commit()
            saved = await _statement_for_institution(
                session, item.id, school.id, level
            )
            return _statement_out(saved)

        @level_router.get(
            "/statements/{statement_id}",
            response_model=SessionStatementOut,
            summary="Зачётная ведомость с результатами",
        )
        async def get_statement(
            statement_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _statement_for_institution(
                session, statement_id, school.id, level
            )
            return _statement_out(item)

        @level_router.patch(
            "/statements/{statement_id}",
            response_model=SessionStatementOut,
            summary="Изменить или утвердить ведомость",
        )
        async def update_statement(
            statement_id: uuid.UUID,
            payload: SessionStatementUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _statement_for_institution(
                session, statement_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in ("statement_number", "status", "profile"):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "teacher_id" in updates and updates["teacher_id"] is not None:
                await _user_for_institution(
                    session,
                    updates["teacher_id"],
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            if "statement_number" in updates:
                number_exists = (
                    await session.execute(
                        select(SessionStatement.id).where(
                            SessionStatement.institution_id == school.id,
                            SessionStatement.statement_number
                            == updates["statement_number"],
                            SessionStatement.id != item.id,
                        )
                    )
                ).scalar_one_or_none()
                if number_exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Statement with this number already exists",
                    )
            if "status" in updates:
                if updates["status"] == "approved":
                    item.approved_at = datetime.now(timezone.utc)
                    item.approved_by_id = current_user.id
                else:
                    item.approved_at = None
                    item.approved_by_id = None
            if "issued_on" in updates and updates["issued_on"] is None:
                raise HTTPException(
                    status_code=422, detail="issued_on cannot be empty"
                )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="session_statement_updated",
                entity_type="session_statement",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            saved = await _statement_for_institution(
                session, item.id, school.id, level
            )
            return _statement_out(saved)

        @level_router.post(
            "/statements/{statement_id}/records/bulk",
            response_model=SessionStatementOut,
            summary="Внести результаты студентов в ведомость",
        )
        async def upsert_statement_records(
            statement_id: uuid.UUID,
            payload: StatementRecordBulk,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            statement = await _statement_for_institution(
                session, statement_id, school.id, level
            )
            if statement.status in {"approved", "archived"}:
                raise HTTPException(
                    status_code=409,
                    detail="Approved or archived statement cannot be changed",
                )
            student_ids = [record.student_id for record in payload.records]
            if len(set(student_ids)) != len(student_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Statement records contain duplicate students",
                )
            memberships = set(
                (
                    await session.execute(
                        select(ClassMembership.user_id).where(
                            ClassMembership.class_id == statement.group_id,
                            ClassMembership.user_id.in_(student_ids),
                            ClassMembership.left_at.is_(None),
                            ClassMembership.role_in_class == "student",
                        )
                    )
                ).scalars().all()
            )
            missing = set(student_ids) - memberships
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail="All students must belong to the statement group",
                )
            existing = {
                record.student_id: record
                for record in (
                    await session.execute(
                        select(StatementRecord).where(
                            StatementRecord.statement_id == statement.id,
                            StatementRecord.student_id.in_(student_ids),
                        )
                    )
                ).scalars().all()
            }
            default_credits = (
                float(statement.component.credits) if statement.component else 0
            )
            for entry in payload.records:
                effective_result = entry.result
                if effective_result == "planned" and entry.grade is not None:
                    effective_result = "passed"
                credits = entry.credits_awarded
                if credits is None:
                    credits = (
                        default_credits
                        if effective_result in {"passed", "exempt", "transferred"}
                        else 0
                    )
                if effective_result == "planned":
                    credits = 0
                record = existing.get(entry.student_id)
                if record is None:
                    record = StatementRecord(
                        statement_id=statement.id,
                        student_id=entry.student_id,
                    )
                    session.add(record)
                record.grade = entry.grade
                record.result = effective_result
                record.credits_awarded = credits
                record.comment = entry.comment
                record.profile = entry.profile
            add_audit_event(
                session,
                action="session_statement_records_updated",
                entity_type="session_statement",
                entity_id=statement.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "records": len(payload.records),
                },
            )
            await session.commit()
            saved = await _statement_for_institution(
                session, statement.id, school.id, level
            )
            return _statement_out(saved)

        @level_router.get(
            "/students/{profile_id}/transcript",
            response_model=TranscriptOut,
            summary="Зачётная книжка и перезачёт кредитов",
        )
        async def get_transcript(
            profile_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            curriculum_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            profile = await _student_profile_for_institution(
                session, profile_id, school.id
            )
            curriculum: EducationCurriculum | None = None
            if curriculum_id is not None:
                curriculum = await _curriculum_for_institution(
                    session, curriculum_id, school.id, level
                )
                if (
                    profile.program_id is not None
                    and curriculum.program_id != profile.program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Curriculum belongs to another program",
                    )
            elif profile.program_id is not None:
                curriculum = (
                    await session.execute(
                        select(EducationCurriculum)
                        .where(
                            EducationCurriculum.institution_id == school.id,
                            EducationCurriculum.education_level == level,
                            EducationCurriculum.program_id
                            == profile.program_id,
                            EducationCurriculum.status != "archived",
                        )
                        .options(selectinload(EducationCurriculum.components))
                        .order_by(
                            EducationCurriculum.academic_year.desc(),
                            EducationCurriculum.created_at.desc(),
                        )
                    )
                ).scalars().first()
            records = (
                await session.execute(
                    select(StatementRecord)
                    .join(
                        SessionStatement,
                        StatementRecord.statement_id == SessionStatement.id,
                    )
                    .where(
                        SessionStatement.institution_id == school.id,
                        SessionStatement.education_level == level,
                        StatementRecord.student_id == profile.user_id,
                        SessionStatement.status == "approved",
                    )
                    .options(
                        selectinload(StatementRecord.statement).selectinload(
                            SessionStatement.session
                        ),
                        selectinload(StatementRecord.statement).selectinload(
                            SessionStatement.component
                        ),
                    )
                    .order_by(SessionStatement.issued_on.desc())
                )
            ).scalars().all()
            transfers = (
                await session.execute(
                    select(CreditTransfer)
                    .where(
                        CreditTransfer.institution_id == school.id,
                        CreditTransfer.education_level == level,
                        CreditTransfer.student_id == profile.user_id,
                        CreditTransfer.status == "approved",
                    )
                    .options(selectinload(CreditTransfer.target_component))
                    .order_by(CreditTransfer.decided_at.desc())
                )
            ).scalars().all()
            items: list[TranscriptItemOut] = []
            for record in records:
                statement = record.statement
                if (
                    statement is None
                    or record.result not in {"passed", "exempt", "transferred"}
                ):
                    continue
                component = statement.component
                items.append(
                    TranscriptItemOut(
                        component_id=component.id if component else None,
                        component_code=component.code if component else "",
                        component_name=component.name if component else "",
                        semester=component.semester if component else None,
                        credits=float(record.credits_awarded or 0),
                        grade=record.grade,
                        result=record.result,  # type: ignore[arg-type]
                        source="statement",
                        academic_year=(
                            statement.session.academic_year
                            if statement.session
                            else ""
                        ),
                        statement_id=statement.id,
                        statement_number=statement.statement_number,
                        issued_on=statement.issued_on,
                    )
                )
            credited_components = {
                item.component_id for item in items if item.component_id is not None
            }
            for transfer in transfers:
                if (
                    transfer.target_component_id is not None
                    and transfer.target_component_id in credited_components
                ):
                    continue
                component = transfer.target_component
                items.append(
                    TranscriptItemOut(
                        component_id=(
                            component.id if component else transfer.target_component_id
                        ),
                        component_code=transfer.source_component_code,
                        component_name=transfer.source_component_name,
                        semester=component.semester if component else None,
                        credits=float(transfer.awarded_credits or 0),
                        grade=transfer.source_grade,
                        result="recognized",
                        source="transfer",
                        academic_year=transfer.source_academic_year,
                        transfer_id=transfer.id,
                        document_number=transfer.document_number,
                        decided_at=transfer.decided_at,
                    )
                )
                if transfer.target_component_id is not None:
                    credited_components.add(transfer.target_component_id)
            items.sort(
                key=lambda item: (
                    item.semester or 99,
                    item.component_code,
                    item.academic_year,
                )
            )
            total_credits = round(sum(item.credits for item in items), 2)
            curriculum_total = (
                round(
                    sum(float(component.credits) for component in curriculum.components),
                    2,
                )
                if curriculum is not None
                else 0
            )
            progress = (
                min(100, round(total_credits / curriculum_total * 100))
                if curriculum_total > 0
                else 0
            )
            return TranscriptOut(
                student_id=profile.user_id,
                login=profile.user.login if profile.user else "",
                full_name=profile.user.full_name if profile.user else "",
                record_book_number=profile.record_book_number,
                program_id=profile.program_id,
                program_name=profile.program.name if profile.program else None,
                group_id=profile.group_id,
                group_name=profile.group.display_name if profile.group else None,
                curriculum_id=curriculum.id if curriculum is not None else None,
                curriculum_name=(
                    curriculum.name if curriculum is not None else None
                ),
                academic_year=(
                    curriculum.academic_year if curriculum is not None else None
                ),
                total_credits=total_credits,
                curriculum_total_credits=curriculum_total,
                progress_percent=progress,
                items=items,
                generated_at=datetime.now(timezone.utc),
            )

        @level_router.get(
            "/credit-transfers",
            response_model=list[CreditTransferOut],
            summary="Перезачёт кредитов",
        )
        async def list_credit_transfers(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            student_id: uuid.UUID | None = Query(default=None),
            status: str | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            if status is not None and status not in (
                "draft",
                "pending",
                "approved",
                "rejected",
                "archived",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown credit transfer status"
                )
            stmt = (
                select(CreditTransfer)
                .where(
                    CreditTransfer.institution_id == school.id,
                    CreditTransfer.education_level == level,
                )
                .options(
                    selectinload(CreditTransfer.student),
                    selectinload(CreditTransfer.target_program),
                    selectinload(CreditTransfer.target_component),
                )
                .order_by(CreditTransfer.created_at.desc())
            )
            if student_id is not None:
                stmt = stmt.where(CreditTransfer.student_id == student_id)
            if status is not None:
                stmt = stmt.where(CreditTransfer.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            return [_credit_transfer_out(item) for item in rows]

        @level_router.post(
            "/credit-transfers",
            response_model=CreditTransferOut,
            status_code=201,
            summary="Создать перезачёт кредитов",
        )
        async def create_credit_transfer(
            payload: CreditTransferCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            student = await _user_for_institution(
                session, payload.student_id, school.id
            )
            profile = (
                await session.execute(
                    select(StudentAcademicProfile).where(
                        StudentAcademicProfile.user_id == student.id,
                        StudentAcademicProfile.institution_id == school.id,
                    )
                )
            ).scalar_one_or_none()
            if profile is None:
                raise HTTPException(
                    status_code=400,
                    detail="Student academic profile not found",
                )
            target_program_id = payload.target_program_id
            if target_program_id is not None:
                await _program_for_institution(
                    session, target_program_id, school.id, level
                )
            target_component = None
            if payload.target_component_id is not None:
                target_component = await _component_for_institution(
                    session, payload.target_component_id, school.id, level
                )
                component_program_id = target_component.curriculum.program_id
                if (
                    target_program_id is not None
                    and component_program_id != target_program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Target component belongs to another program",
                    )
                target_program_id = target_program_id or component_program_id
            exists = (
                await session.execute(
                    select(CreditTransfer.id).where(
                        CreditTransfer.institution_id == school.id,
                        CreditTransfer.student_id == student.id,
                        CreditTransfer.source_institution
                        == payload.source_institution,
                        CreditTransfer.source_component_code
                        == payload.source_component_code,
                        CreditTransfer.source_academic_year
                        == payload.source_academic_year,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Credit transfer for this source already exists",
                )
            status = payload.status
            decided = status in {"approved", "rejected"}
            item = CreditTransfer(
                institution_id=school.id,
                education_level=level,
                student_id=student.id,
                target_program_id=target_program_id,
                target_component_id=payload.target_component_id,
                source_institution=payload.source_institution,
                source_program=payload.source_program,
                source_component_code=payload.source_component_code,
                source_component_name=payload.source_component_name,
                source_academic_year=payload.source_academic_year,
                source_credits=payload.source_credits,
                awarded_credits=(
                    payload.awarded_credits
                    if payload.awarded_credits is not None
                    else payload.source_credits
                ),
                source_grade=payload.source_grade,
                document_number=payload.document_number,
                reason=payload.reason,
                status=status,
                decided_at=datetime.now(timezone.utc) if decided else None,
                decided_by_id=current_user.id if decided else None,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="credit_transfer_created",
                entity_type="credit_transfer",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "student_id": str(student.id),
                    "status": status,
                },
            )
            await session.commit()
            saved = await _credit_transfer_for_institution(
                session, item.id, school.id, level
            )
            return _credit_transfer_out(saved)

        @level_router.patch(
            "/credit-transfers/{transfer_id}",
            response_model=CreditTransferOut,
            summary="Изменить решение о перезачёте кредитов",
        )
        async def update_credit_transfer(
            transfer_id: uuid.UUID,
            payload: CreditTransferUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _credit_transfer_for_institution(
                session, transfer_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in ("awarded_credits", "status", "profile"):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "target_program_id" in updates and updates["target_program_id"] is not None:
                await _program_for_institution(
                    session,
                    updates["target_program_id"],
                    school.id,
                    level,
                )
            if "target_component_id" in updates and updates["target_component_id"] is not None:
                component = await _component_for_institution(
                    session,
                    updates["target_component_id"],
                    school.id,
                    level,
                )
                target_program_id = updates.get(
                    "target_program_id", item.target_program_id
                )
                if (
                    target_program_id is not None
                    and component.curriculum.program_id != target_program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Target component belongs to another program",
                    )
            if "status" in updates:
                if updates["status"] in {"approved", "rejected"}:
                    item.decided_at = datetime.now(timezone.utc)
                    item.decided_by_id = current_user.id
                else:
                    item.decided_at = None
                    item.decided_by_id = None
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="credit_transfer_updated",
                entity_type="credit_transfer",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            saved = await _credit_transfer_for_institution(
                session, item.id, school.id, level
            )
            return _credit_transfer_out(saved)

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
