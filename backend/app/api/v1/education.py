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
from sqlalchemy import delete, func, or_, select
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
    Competency,
    ComponentCompetency,
    CreditTransfer,
    CurriculumComponent,
    EducationCurriculum,
    EducationProgram,
    PracticeContract,
    PracticeDiaryEntry,
    PracticePlace,
    PracticePlacement,
    ProgramCompetency,
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
    CompetencyCreate,
    CompetencyMatrixBulk,
    CompetencyMatrixComponentOut,
    CompetencyMatrixCompetencyOut,
    CompetencyMatrixLinkOut,
    CompetencyMatrixOut,
    CompetencyOut,
    CompetencyUpdate,
    ComponentCompetencyOut,
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
    PracticeAssessmentIn,
    PracticeContractCreate,
    PracticeContractOut,
    PracticeContractUpdate,
    PracticeDiaryEntryCreate,
    PracticeDiaryEntryOut,
    PracticeDiaryEntryUpdate,
    PracticePlaceCreate,
    PracticePlaceOut,
    PracticePlaceUpdate,
    PracticePlacementCreate,
    PracticePlacementOut,
    PracticePlacementUpdate,
    ProgramCompetencyBulk,
    ProgramCompetencyOut,
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


def _competency_out(item: Competency) -> CompetencyOut:
    return CompetencyOut.model_validate(item)


def _program_competency_out(link: ProgramCompetency) -> ProgramCompetencyOut:
    competency = link.competency
    return ProgramCompetencyOut(
        id=link.id,
        program_id=link.program_id,
        competency_id=link.competency_id,
        code=competency.code if competency else "",
        name=competency.name if competency else "",
        competency_type=(
            competency.competency_type  # type: ignore[arg-type]
            if competency
            else "other"
        ),
        target_level=link.target_level,
        weight=float(link.weight or 0),
        profile=link.profile or {},
    )


def _component_competency_out(
    link: ComponentCompetency,
) -> ComponentCompetencyOut:
    competency = link.competency
    return ComponentCompetencyOut(
        id=link.id,
        component_id=link.component_id,
        competency_id=link.competency_id,
        code=competency.code if competency else "",
        name=competency.name if competency else "",
        competency_type=(
            competency.competency_type  # type: ignore[arg-type]
            if competency
            else "other"
        ),
        weight=float(link.weight or 0),
        profile=link.profile or {},
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


async def _competency_for_institution(
    session: AsyncSession,
    competency_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> Competency:
    item = await session.get(Competency, competency_id)
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Competency not found")
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


async def _build_competency_matrix(
    session: AsyncSession,
    *,
    curriculum: EducationCurriculum,
    school_id: uuid.UUID,
    level: str,
) -> CompetencyMatrixOut:
    components = sorted(
        curriculum.components,
        key=lambda item: (item.semester, item.order_index, item.code),
    )
    component_ids = [component.id for component in components]
    competencies = (
        (
            await session.execute(
                select(Competency)
                .where(
                    Competency.institution_id == school_id,
                    Competency.education_level == level,
                )
                .order_by(Competency.code)
            )
        )
        .scalars()
        .all()
    )
    links: list[ComponentCompetency] = []
    if component_ids:
        links = (
            (
                await session.execute(
                    select(ComponentCompetency)
                    .where(ComponentCompetency.component_id.in_(component_ids))
                    .options(selectinload(ComponentCompetency.competency))
                    .order_by(
                        ComponentCompetency.component_id,
                        ComponentCompetency.competency_id,
                    )
                )
            )
            .scalars()
            .all()
        )
    return CompetencyMatrixOut(
        curriculum_id=curriculum.id,
        curriculum_name=curriculum.name,
        program_id=curriculum.program_id,
        components=[
            CompetencyMatrixComponentOut(
                id=component.id,
                code=component.code,
                name=component.name,
                semester=component.semester,
                component_type=component.component_type,  # type: ignore[arg-type]
            )
            for component in components
        ],
        competencies=[
            CompetencyMatrixCompetencyOut(
                id=competency.id,
                code=competency.code,
                name=competency.name,
                competency_type=competency.competency_type,  # type: ignore[arg-type]
            )
            for competency in competencies
        ],
        links=[
            CompetencyMatrixLinkOut(
                component_id=link.component_id,
                competency_id=link.competency_id,
                weight=float(link.weight or 0),
            )
            for link in links
        ],
    )


def _practice_place_out(item: PracticePlace) -> PracticePlaceOut:
    return PracticePlaceOut.model_validate(item)


def _practice_contract_out(item: PracticeContract) -> PracticeContractOut:
    return PracticeContractOut(
        id=item.id,
        institution_id=item.institution_id,
        education_level=item.education_level,  # type: ignore[arg-type]
        practice_place_id=item.practice_place_id,
        place_name=item.place.name if item.place else "",
        program_id=item.program_id,
        program_name=item.program.name if item.program else None,
        component_id=item.component_id,
        component_code=item.component.code if item.component else None,
        component_name=item.component.name if item.component else None,
        contract_number=item.contract_number,
        academic_year=item.academic_year,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        signed_on=item.signed_on,
        status=item.status,  # type: ignore[arg-type]
        responsible_id=item.responsible_id,
        responsible_name=(
            item.responsible.full_name if item.responsible else None
        ),
        document_number=item.document_number,
        notes=item.notes,
        profile=item.profile or {},
        placements_count=len(item.placements),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _practice_completed_hours(item: PracticePlacement) -> float:
    return round(
        sum(
            float(entry.hours or 0)
            for entry in item.diary_entries
            if entry.status == "approved"
        ),
        2,
    )


def _practice_placement_out(item: PracticePlacement) -> PracticePlacementOut:
    contract = item.contract
    return PracticePlacementOut(
        id=item.id,
        contract_id=item.contract_id,
        contract_number=contract.contract_number if contract else "",
        place_name=(
            contract.place.name if contract and contract.place else ""
        ),
        institution_id=item.institution_id,
        education_level=item.education_level,  # type: ignore[arg-type]
        student_id=item.student_id,
        student_login=item.student.login if item.student else "",
        student_name=item.student.full_name if item.student else "",
        group_id=item.group_id,
        group_name=item.group.display_name if item.group else None,
        component_id=item.component_id,
        component_code=item.component.code if item.component else None,
        component_name=item.component.name if item.component else None,
        supervisor_id=item.supervisor_id,
        supervisor_name=(
            item.supervisor.full_name if item.supervisor else None
        ),
        enterprise_supervisor=item.enterprise_supervisor,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        total_hours=item.total_hours,
        completed_hours=_practice_completed_hours(item),
        status=item.status,  # type: ignore[arg-type]
        result=item.result,  # type: ignore[arg-type]
        grade=item.grade,
        assessed_at=item.assessed_at,
        assessed_by_id=item.assessed_by_id,
        notes=item.notes,
        profile=item.profile or {},
        diary_entries_count=len(item.diary_entries),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _practice_diary_out(item: PracticeDiaryEntry) -> PracticeDiaryEntryOut:
    return PracticeDiaryEntryOut(
        id=item.id,
        placement_id=item.placement_id,
        entry_date=item.entry_date,
        hours=float(item.hours or 0),
        activity=item.activity,
        outcome=item.outcome,
        supervisor_comment=item.supervisor_comment,
        status=item.status,  # type: ignore[arg-type]
        submitted_at=item.submitted_at,
        approved_at=item.approved_at,
        approved_by_id=item.approved_by_id,
        profile=item.profile or {},
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _practice_place_for_institution(
    session: AsyncSession,
    place_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> PracticePlace:
    item = await session.get(PracticePlace, place_id)
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(status_code=404, detail="Practice place not found")
    return item


async def _practice_contract_for_institution(
    session: AsyncSession,
    contract_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> PracticeContract:
    item = (
        await session.execute(
            select(PracticeContract)
            .where(PracticeContract.id == contract_id)
            .options(
                selectinload(PracticeContract.place),
                selectinload(PracticeContract.program),
                selectinload(PracticeContract.component),
                selectinload(PracticeContract.responsible),
                selectinload(PracticeContract.placements),
            )
        )
    ).scalar_one_or_none()
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(
            status_code=404, detail="Practice contract not found"
        )
    return item


async def _practice_placement_for_institution(
    session: AsyncSession,
    placement_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> PracticePlacement:
    item = (
        await session.execute(
            select(PracticePlacement)
            .where(PracticePlacement.id == placement_id)
            .options(
                selectinload(PracticePlacement.contract).selectinload(
                    PracticeContract.place
                ),
                selectinload(PracticePlacement.student),
                selectinload(PracticePlacement.group),
                selectinload(PracticePlacement.component),
                selectinload(PracticePlacement.supervisor),
                selectinload(PracticePlacement.diary_entries),
            )
        )
    ).scalar_one_or_none()
    if (
        item is None
        or item.institution_id != school_id
        or item.education_level != level
    ):
        raise HTTPException(
            status_code=404, detail="Practice placement not found"
        )
    return item


async def _practice_diary_for_institution(
    session: AsyncSession,
    entry_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> PracticeDiaryEntry:
    item = (
        await session.execute(
            select(PracticeDiaryEntry)
            .where(PracticeDiaryEntry.id == entry_id)
            .options(selectinload(PracticeDiaryEntry.placement))
        )
    ).scalar_one_or_none()
    if (
        item is None
        or item.placement is None
        or item.placement.institution_id != school_id
        or item.placement.education_level != level
    ):
        raise HTTPException(
            status_code=404, detail="Practice diary entry not found"
        )
    return item


def _ensure_practice_dates(
    starts_on: date,
    ends_on: date,
    contract: PracticeContract | None = None,
) -> None:
    if ends_on < starts_on:
        raise HTTPException(
            status_code=422,
            detail="ends_on cannot be earlier than starts_on",
        )
    if contract is not None and (
        starts_on < contract.starts_on or ends_on > contract.ends_on
    ):
        raise HTTPException(
            status_code=400,
            detail="Placement dates must be inside the contract period",
        )


async def _practice_component_for_institution(
    session: AsyncSession,
    component_id: uuid.UUID,
    school_id: uuid.UUID,
    level: str,
) -> CurriculumComponent:
    component = await _component_for_institution(
        session, component_id, school_id, level
    )
    if component.component_type not in {"practice", "internship"}:
        raise HTTPException(
            status_code=400,
            detail="Curriculum component must be a practice or internship",
        )
    return component


async def _practice_student_for_institution(
    session: AsyncSession,
    student_id: uuid.UUID,
    school_id: uuid.UUID,
) -> User:
    student = await _user_for_institution(
        session, student_id, school_id, {"student"}
    )
    profile = (
        await session.execute(
            select(StudentAcademicProfile.id).where(
                StudentAcademicProfile.user_id == student.id,
                StudentAcademicProfile.institution_id == school_id,
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Student academic profile not found",
        )
    return student


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
            "/competencies",
            response_model=list[CompetencyOut],
            summary="Профессиональные компетенции",
        )
        async def list_competencies(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            search: str | None = Query(default=None, max_length=100),
            competency_type: str | None = Query(default=None),
            is_active: bool | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            if competency_type is not None and competency_type not in (
                "universal",
                "general",
                "professional",
                "other",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown competency type"
                )
            stmt = (
                select(Competency)
                .where(
                    Competency.institution_id == school.id,
                    Competency.education_level == level,
                )
                .order_by(Competency.code)
            )
            if search:
                pattern = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        Competency.code.ilike(pattern),
                        Competency.name.ilike(pattern),
                    )
                )
            if competency_type is not None:
                stmt = stmt.where(
                    Competency.competency_type == competency_type
                )
            if is_active is not None:
                stmt = stmt.where(Competency.is_active.is_(is_active))
            rows = (await session.execute(stmt)).scalars().all()
            return [_competency_out(item) for item in rows]

        @level_router.post(
            "/competencies",
            response_model=CompetencyOut,
            status_code=201,
            summary="Создать компетенцию",
        )
        async def create_competency(
            payload: CompetencyCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            code = payload.code.strip()
            name = payload.name.strip()
            if not code or not name:
                raise HTTPException(
                    status_code=422, detail="Code and name cannot be empty"
                )
            exists = (
                await session.execute(
                    select(Competency.id).where(
                        Competency.institution_id == school.id,
                        Competency.code == code,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Competency with this code already exists",
                )
            item = Competency(
                institution_id=school.id,
                education_level=level,
                code=code,
                name=name,
                description=payload.description,
                competency_type=payload.competency_type,
                profile=payload.profile,
                is_active=payload.is_active,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="competency_created",
                entity_type="competency",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "code": item.code,
                    "competency_type": item.competency_type,
                },
            )
            await session.commit()
            await session.refresh(item)
            return _competency_out(item)

        @level_router.patch(
            "/competencies/{competency_id}",
            response_model=CompetencyOut,
            summary="Изменить компетенцию",
        )
        async def update_competency(
            competency_id: uuid.UUID,
            payload: CompetencyUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _competency_for_institution(
                session, competency_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in (
                "code",
                "name",
                "competency_type",
                "profile",
                "is_active",
            ):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "code" in updates:
                updates["code"] = updates["code"].strip()
                if not updates["code"]:
                    raise HTTPException(
                        status_code=422, detail="Code cannot be empty"
                    )
                number_exists = (
                    await session.execute(
                        select(Competency.id).where(
                            Competency.institution_id == school.id,
                            Competency.code == updates["code"],
                            Competency.id != item.id,
                        )
                    )
                ).scalar_one_or_none()
                if number_exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Competency with this code already exists",
                    )
            if "name" in updates:
                updates["name"] = updates["name"].strip()
                if not updates["name"]:
                    raise HTTPException(
                        status_code=422, detail="Name cannot be empty"
                    )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="competency_updated",
                entity_type="competency",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(item)
            return _competency_out(item)

        @level_router.get(
            "/programs/{program_id}/competencies",
            response_model=list[ProgramCompetencyOut],
            summary="Компетенции образовательной программы",
        )
        async def list_program_competencies(
            program_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            program = await _program_for_institution(
                session, program_id, school.id, level
            )
            rows = (
                (
                    await session.execute(
                        select(ProgramCompetency)
                        .where(ProgramCompetency.program_id == program.id)
                        .options(
                            selectinload(ProgramCompetency.competency)
                        )
                        .order_by(ProgramCompetency.competency_id)
                    )
                )
                .scalars()
                .all()
            )
            return [_program_competency_out(item) for item in rows]

        @level_router.put(
            "/programs/{program_id}/competencies",
            response_model=list[ProgramCompetencyOut],
            summary="Заменить матрицу компетенций программы",
        )
        async def replace_program_competencies(
            program_id: uuid.UUID,
            payload: ProgramCompetencyBulk,
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
            competency_ids = [item.competency_id for item in payload.items]
            if len(set(competency_ids)) != len(competency_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Program competency list contains duplicates",
                )
            for competency_id in competency_ids:
                await _competency_for_institution(
                    session, competency_id, school.id, level
                )
            await session.execute(
                delete(ProgramCompetency).where(
                    ProgramCompetency.program_id == program.id
                )
            )
            for item in payload.items:
                session.add(
                    ProgramCompetency(
                        program_id=program.id,
                        competency_id=item.competency_id,
                        target_level=item.target_level,
                        weight=item.weight,
                        profile=item.profile,
                    )
                )
            add_audit_event(
                session,
                action="program_competencies_replaced",
                entity_type="education_program",
                entity_id=program.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "competencies": len(payload.items),
                },
            )
            await session.commit()
            rows = (
                (
                    await session.execute(
                        select(ProgramCompetency)
                        .where(ProgramCompetency.program_id == program.id)
                        .options(
                            selectinload(ProgramCompetency.competency)
                        )
                        .order_by(ProgramCompetency.competency_id)
                    )
                )
                .scalars()
                .all()
            )
            return [_program_competency_out(item) for item in rows]

        @level_router.get(
            "/curricula/{curriculum_id}/competency-matrix",
            response_model=CompetencyMatrixOut,
            summary="Матрица компетенций учебного плана",
        )
        async def get_competency_matrix(
            curriculum_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            curriculum = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            return await _build_competency_matrix(
                session,
                curriculum=curriculum,
                school_id=school.id,
                level=level,
            )

        @level_router.put(
            "/curricula/{curriculum_id}/competency-matrix",
            response_model=CompetencyMatrixOut,
            summary="Заменить матрицу компетенций учебного плана",
        )
        async def replace_competency_matrix(
            curriculum_id: uuid.UUID,
            payload: CompetencyMatrixBulk,
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
            component_ids = {
                component.id for component in curriculum.components
            }
            pair_keys = [
                (item.component_id, item.competency_id)
                for item in payload.links
            ]
            if len(set(pair_keys)) != len(pair_keys):
                raise HTTPException(
                    status_code=422,
                    detail="Competency matrix contains duplicate links",
                )
            if any(
                item.component_id not in component_ids
                for item in payload.links
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Component does not belong to the curriculum",
                )
            valid_competencies = set(
                (
                    await session.execute(
                        select(Competency.id).where(
                            Competency.institution_id == school.id,
                            Competency.education_level == level,
                        )
                    )
                ).scalars().all()
            )
            if any(
                item.competency_id not in valid_competencies
                for item in payload.links
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Competency does not belong to the institution",
                )
            if component_ids:
                await session.execute(
                    delete(ComponentCompetency).where(
                        ComponentCompetency.component_id.in_(component_ids)
                    )
                )
            for item in payload.links:
                session.add(
                    ComponentCompetency(
                        component_id=item.component_id,
                        competency_id=item.competency_id,
                        weight=item.weight,
                    )
                )
            add_audit_event(
                session,
                action="component_competencies_replaced",
                entity_type="education_curriculum",
                entity_id=curriculum.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "links": len(payload.links),
                },
            )
            await session.commit()
            refreshed = await _curriculum_for_institution(
                session, curriculum_id, school.id, level
            )
            return await _build_competency_matrix(
                session,
                curriculum=refreshed,
                school_id=school.id,
                level=level,
            )

        @level_router.get(
            "/practice-places",
            response_model=list[PracticePlaceOut],
            summary="Предприятия и организации для практики",
        )
        async def list_practice_places(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            search: str | None = Query(default=None, max_length=100),
            is_active: bool | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            stmt = (
                select(PracticePlace)
                .where(
                    PracticePlace.institution_id == school.id,
                    PracticePlace.education_level == level,
                )
                .order_by(PracticePlace.name)
            )
            if search:
                pattern = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        PracticePlace.code.ilike(pattern),
                        PracticePlace.name.ilike(pattern),
                        PracticePlace.industry.ilike(pattern),
                    )
                )
            if is_active is not None:
                stmt = stmt.where(PracticePlace.is_active.is_(is_active))
            rows = (await session.execute(stmt)).scalars().all()
            return [_practice_place_out(item) for item in rows]

        @level_router.post(
            "/practice-places",
            response_model=PracticePlaceOut,
            status_code=201,
            summary="Добавить предприятие для практики",
        )
        async def create_practice_place(
            payload: PracticePlaceCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            code = payload.code.strip()
            name = payload.name.strip()
            if not code or not name:
                raise HTTPException(
                    status_code=422, detail="Code and name cannot be empty"
                )
            exists = (
                await session.execute(
                    select(PracticePlace.id).where(
                        PracticePlace.institution_id == school.id,
                        PracticePlace.code == code,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Practice place with this code already exists",
                )
            item = PracticePlace(
                institution_id=school.id,
                education_level=level,
                code=code,
                name=name,
                industry=payload.industry,
                address=payload.address,
                contact_person=payload.contact_person,
                contact_phone=payload.contact_phone,
                contact_email=payload.contact_email,
                is_active=payload.is_active,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="practice_place_created",
                entity_type="practice_place",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "code": item.code},
            )
            await session.commit()
            await session.refresh(item)
            return _practice_place_out(item)

        @level_router.patch(
            "/practice-places/{place_id}",
            response_model=PracticePlaceOut,
            summary="Изменить предприятие для практики",
        )
        async def update_practice_place(
            place_id: uuid.UUID,
            payload: PracticePlaceUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _practice_place_for_institution(
                session, place_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in ("code", "name", "is_active", "profile"):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "code" in updates:
                updates["code"] = updates["code"].strip()
                if not updates["code"]:
                    raise HTTPException(
                        status_code=422, detail="Code cannot be empty"
                    )
                number_exists = (
                    await session.execute(
                        select(PracticePlace.id).where(
                            PracticePlace.institution_id == school.id,
                            PracticePlace.code == updates["code"],
                            PracticePlace.id != item.id,
                        )
                    )
                ).scalar_one_or_none()
                if number_exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Practice place with this code already exists",
                    )
            if "name" in updates:
                updates["name"] = updates["name"].strip()
                if not updates["name"]:
                    raise HTTPException(
                        status_code=422, detail="Name cannot be empty"
                    )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="practice_place_updated",
                entity_type="practice_place",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(item)
            return _practice_place_out(item)

        @level_router.get(
            "/practice-contracts",
            response_model=list[PracticeContractOut],
            summary="Договоры с предприятиями",
        )
        async def list_practice_contracts(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            practice_place_id: uuid.UUID | None = Query(default=None),
            program_id: uuid.UUID | None = Query(default=None),
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
                "draft",
                "signed",
                "active",
                "completed",
                "terminated",
                "archived",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown contract status"
                )
            stmt = (
                select(PracticeContract)
                .where(
                    PracticeContract.institution_id == school.id,
                    PracticeContract.education_level == level,
                )
                .options(
                    selectinload(PracticeContract.place),
                    selectinload(PracticeContract.program),
                    selectinload(PracticeContract.component),
                    selectinload(PracticeContract.responsible),
                    selectinload(PracticeContract.placements),
                )
                .order_by(
                    PracticeContract.academic_year.desc(),
                    PracticeContract.starts_on.desc(),
                    PracticeContract.contract_number,
                )
            )
            if practice_place_id is not None:
                stmt = stmt.where(
                    PracticeContract.practice_place_id == practice_place_id
                )
            if program_id is not None:
                stmt = stmt.where(PracticeContract.program_id == program_id)
            if academic_year is not None:
                stmt = stmt.where(
                    PracticeContract.academic_year == academic_year
                )
            if status is not None:
                stmt = stmt.where(PracticeContract.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            return [_practice_contract_out(item) for item in rows]

        @level_router.post(
            "/practice-contracts",
            response_model=PracticeContractOut,
            status_code=201,
            summary="Заключить договор с предприятием",
        )
        async def create_practice_contract(
            payload: PracticeContractCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            contract_number = payload.contract_number.strip()
            if not contract_number:
                raise HTTPException(
                    status_code=422,
                    detail="Contract number cannot be empty",
                )
            await _practice_place_for_institution(
                session, payload.practice_place_id, school.id, level
            )
            if payload.program_id is not None:
                await _program_for_institution(
                    session, payload.program_id, school.id, level
                )
            program_id = payload.program_id
            if payload.component_id is not None:
                component = await _practice_component_for_institution(
                    session, payload.component_id, school.id, level
                )
                component_program_id = component.curriculum.program_id
                if (
                    program_id is not None
                    and component_program_id != program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Practice component belongs to another program",
                    )
                program_id = program_id or component_program_id
            _ensure_practice_dates(payload.starts_on, payload.ends_on)
            if payload.signed_on is not None and payload.signed_on > payload.ends_on:
                raise HTTPException(
                    status_code=422,
                    detail="signed_on cannot be later than ends_on",
                )
            if payload.responsible_id is not None:
                await _user_for_institution(
                    session,
                    payload.responsible_id,
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            exists = (
                await session.execute(
                    select(PracticeContract.id).where(
                        PracticeContract.institution_id == school.id,
                        PracticeContract.contract_number == contract_number,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Contract with this number already exists",
                )
            item = PracticeContract(
                institution_id=school.id,
                education_level=level,
                practice_place_id=payload.practice_place_id,
                program_id=program_id,
                component_id=payload.component_id,
                contract_number=contract_number,
                academic_year=payload.academic_year,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                signed_on=payload.signed_on,
                status=payload.status,
                responsible_id=payload.responsible_id,
                document_number=payload.document_number,
                notes=payload.notes,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="practice_contract_created",
                entity_type="practice_contract",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "contract_number": item.contract_number,
                },
            )
            await session.commit()
            saved = await _practice_contract_for_institution(
                session, item.id, school.id, level
            )
            return _practice_contract_out(saved)

        @level_router.patch(
            "/practice-contracts/{contract_id}",
            response_model=PracticeContractOut,
            summary="Изменить договор с предприятием",
        )
        async def update_practice_contract(
            contract_id: uuid.UUID,
            payload: PracticeContractUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _practice_contract_for_institution(
                session, contract_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in (
                "practice_place_id",
                "contract_number",
                "academic_year",
                "starts_on",
                "ends_on",
                "status",
                "profile",
            ):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "practice_place_id" in updates:
                await _practice_place_for_institution(
                    session,
                    updates["practice_place_id"],
                    school.id,
                    level,
                )
            new_program_id = updates.get("program_id", item.program_id)
            if "program_id" in updates and updates["program_id"] is not None:
                await _program_for_institution(
                    session,
                    updates["program_id"],
                    school.id,
                    level,
                )
            new_component_id = updates.get("component_id", item.component_id)
            if new_component_id is not None:
                component = await _practice_component_for_institution(
                    session, new_component_id, school.id, level
                )
                component_program_id = component.curriculum.program_id
                if new_program_id is None:
                    updates["program_id"] = component_program_id
                elif component_program_id != new_program_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Practice component belongs to another program",
                    )
            starts_on = updates.get("starts_on", item.starts_on)
            ends_on = updates.get("ends_on", item.ends_on)
            _ensure_practice_dates(starts_on, ends_on)
            signed_on = updates.get("signed_on", item.signed_on)
            if signed_on is not None and signed_on > ends_on:
                raise HTTPException(
                    status_code=422,
                    detail="signed_on cannot be later than ends_on",
                )
            if item.placements:
                new_program_id = updates.get("program_id", item.program_id)
                new_component_id = updates.get("component_id", item.component_id)
                if (
                    new_program_id != item.program_id
                    or new_component_id != item.component_id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Cannot change program or practice component "
                            "of a contract with placements"
                        ),
                    )
                if "starts_on" in updates or "ends_on" in updates:
                    if any(
                        placement.starts_on < starts_on
                        or placement.ends_on > ends_on
                        for placement in item.placements
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "Placements fall outside the new contract period"
                            ),
                        )
            if "responsible_id" in updates and updates["responsible_id"] is not None:
                await _user_for_institution(
                    session,
                    updates["responsible_id"],
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            if "contract_number" in updates:
                updates["contract_number"] = updates["contract_number"].strip()
                if not updates["contract_number"]:
                    raise HTTPException(
                        status_code=422,
                        detail="Contract number cannot be empty",
                    )
                number_exists = (
                    await session.execute(
                        select(PracticeContract.id).where(
                            PracticeContract.institution_id == school.id,
                            PracticeContract.contract_number
                            == updates["contract_number"],
                            PracticeContract.id != item.id,
                        )
                    )
                ).scalar_one_or_none()
                if number_exists is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Contract with this number already exists",
                    )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="practice_contract_updated",
                entity_type="practice_contract",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            saved = await _practice_contract_for_institution(
                session, item.id, school.id, level
            )
            return _practice_contract_out(saved)

        @level_router.get(
            "/practice-placements",
            response_model=list[PracticePlacementOut],
            summary="Практиканты и места практики",
        )
        async def list_practice_placements(
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            contract_id: uuid.UUID | None = Query(default=None),
            group_id: uuid.UUID | None = Query(default=None),
            student_id: uuid.UUID | None = Query(default=None),
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
                "failed",
                "cancelled",
                "archived",
            ):
                raise HTTPException(
                    status_code=422, detail="Unknown placement status"
                )
            stmt = (
                select(PracticePlacement)
                .where(
                    PracticePlacement.institution_id == school.id,
                    PracticePlacement.education_level == level,
                )
                .options(
                    selectinload(PracticePlacement.contract).selectinload(
                        PracticeContract.place
                    ),
                    selectinload(PracticePlacement.student),
                    selectinload(PracticePlacement.group),
                    selectinload(PracticePlacement.component),
                    selectinload(PracticePlacement.supervisor),
                    selectinload(PracticePlacement.diary_entries),
                )
                .order_by(
                    PracticePlacement.starts_on.desc(),
                    PracticePlacement.created_at.desc(),
                )
            )
            if contract_id is not None:
                stmt = stmt.where(
                    PracticePlacement.contract_id == contract_id
                )
            if group_id is not None:
                stmt = stmt.where(PracticePlacement.group_id == group_id)
            if student_id is not None:
                stmt = stmt.where(PracticePlacement.student_id == student_id)
            if status is not None:
                stmt = stmt.where(PracticePlacement.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            return [_practice_placement_out(item) for item in rows]

        @level_router.post(
            "/practice-placements",
            response_model=PracticePlacementOut,
            status_code=201,
            summary="Назначить практику обучающемуся",
        )
        async def create_practice_placement(
            payload: PracticePlacementCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            contract = await _practice_contract_for_institution(
                session, payload.contract_id, school.id, level
            )
            await _practice_student_for_institution(
                session, payload.student_id, school.id
            )
            if payload.group_id is not None:
                await _group_for_institution(
                    session, payload.group_id, school.id, level
                )
            if payload.supervisor_id is not None:
                await _user_for_institution(
                    session,
                    payload.supervisor_id,
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            component = None
            component_id = (
                payload.component_id
                if payload.component_id is not None
                else contract.component_id
            )
            if component_id is not None:
                component = await _practice_component_for_institution(
                    session, component_id, school.id, level
                )
                if (
                    contract.program_id is not None
                    and component.curriculum.program_id
                    != contract.program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Practice component belongs to another program",
                    )
            _ensure_practice_dates(
                payload.starts_on, payload.ends_on, contract
            )
            exists = (
                await session.execute(
                    select(PracticePlacement.id).where(
                        PracticePlacement.contract_id == contract.id,
                        PracticePlacement.student_id == payload.student_id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Student already has a placement in this contract",
                )
            total_hours = payload.total_hours
            if total_hours == 0 and component is not None:
                total_hours = component.academic_hours
            item = PracticePlacement(
                contract_id=contract.id,
                institution_id=school.id,
                education_level=level,
                student_id=payload.student_id,
                group_id=payload.group_id,
                component_id=component_id,
                supervisor_id=payload.supervisor_id,
                enterprise_supervisor=payload.enterprise_supervisor,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                total_hours=total_hours,
                status=payload.status,
                notes=payload.notes,
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="practice_placement_created",
                entity_type="practice_placement",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "contract_id": str(contract.id),
                    "student_id": str(payload.student_id),
                },
            )
            await session.commit()
            saved = await _practice_placement_for_institution(
                session, item.id, school.id, level
            )
            return _practice_placement_out(saved)

        @level_router.patch(
            "/practice-placements/{placement_id}",
            response_model=PracticePlacementOut,
            summary="Изменить практику обучающегося",
        )
        async def update_practice_placement(
            placement_id: uuid.UUID,
            payload: PracticePlacementUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _practice_placement_for_institution(
                session, placement_id, school.id, level
            )
            updates = payload.model_dump(exclude_unset=True)
            for field in (
                "starts_on",
                "ends_on",
                "total_hours",
                "status",
                "profile",
            ):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            if "group_id" in updates and updates["group_id"] is not None:
                await _group_for_institution(
                    session, updates["group_id"], school.id, level
                )
            if "supervisor_id" in updates and updates["supervisor_id"] is not None:
                await _user_for_institution(
                    session,
                    updates["supervisor_id"],
                    school.id,
                    {"teacher", "methodologist", "admin"},
                )
            new_component_id = updates.get("component_id", item.component_id)
            if new_component_id is not None:
                component = await _practice_component_for_institution(
                    session, new_component_id, school.id, level
                )
                contract = item.contract
                if (
                    contract is not None
                    and contract.program_id is not None
                    and component.curriculum.program_id != contract.program_id
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Practice component belongs to another program",
                    )
            starts_on = updates.get("starts_on", item.starts_on)
            ends_on = updates.get("ends_on", item.ends_on)
            contract = item.contract
            _ensure_practice_dates(starts_on, ends_on, contract)
            total_hours = updates.get("total_hours", item.total_hours)
            if total_hours > 0 and _practice_completed_hours(item) > total_hours:
                raise HTTPException(
                    status_code=422,
                    detail="Approved hours exceed the new total hours",
                )
            if any(
                entry.entry_date < starts_on or entry.entry_date > ends_on
                for entry in item.diary_entries
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Diary entries fall outside the new practice period",
                )
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="practice_placement_updated",
                entity_type="practice_placement",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            saved = await _practice_placement_for_institution(
                session, item.id, school.id, level
            )
            return _practice_placement_out(saved)

        @level_router.post(
            "/practice-placements/{placement_id}/assessment",
            response_model=PracticePlacementOut,
            summary="Оценить практику обучающегося",
        )
        async def assess_practice_placement(
            placement_id: uuid.UUID,
            payload: PracticeAssessmentIn,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _practice_placement_for_institution(
                session, placement_id, school.id, level
            )
            item.result = payload.result
            if payload.result == "not_assessed":
                item.grade = None
                item.assessed_at = None
                item.assessed_by_id = None
            else:
                item.grade = payload.grade
                item.assessed_at = datetime.now(timezone.utc)
                item.assessed_by_id = current_user.id
            add_audit_event(
                session,
                action="practice_placement_assessed",
                entity_type="practice_placement",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "result": payload.result,
                    "grade": payload.grade,
                },
            )
            await session.commit()
            saved = await _practice_placement_for_institution(
                session, item.id, school.id, level
            )
            return _practice_placement_out(saved)

        @level_router.get(
            "/practice-placements/{placement_id}/diary",
            response_model=list[PracticeDiaryEntryOut],
            summary="Дневник практики",
        )
        async def list_practice_diary(
            placement_id: uuid.UUID,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(read_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            placement = await _practice_placement_for_institution(
                session, placement_id, school.id, level
            )
            entries = sorted(
                placement.diary_entries,
                key=lambda entry: (entry.entry_date, entry.created_at),
            )
            return [_practice_diary_out(entry) for entry in entries]

        @level_router.post(
            "/practice-placements/{placement_id}/diary",
            response_model=PracticeDiaryEntryOut,
            status_code=201,
            summary="Добавить запись дневника практики",
        )
        async def create_practice_diary_entry(
            placement_id: uuid.UUID,
            payload: PracticeDiaryEntryCreate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            placement = await _practice_placement_for_institution(
                session, placement_id, school.id, level
            )
            if placement.status in {"completed", "cancelled", "archived"}:
                raise HTTPException(
                    status_code=409,
                    detail="Completed or archived placement cannot be changed",
                )
            if (
                payload.entry_date < placement.starts_on
                or payload.entry_date > placement.ends_on
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Entry date must be inside the placement period",
                )
            activity = payload.activity.strip()
            if not activity:
                raise HTTPException(
                    status_code=422, detail="Activity cannot be empty"
                )
            if payload.status == "approved":
                approved_hours = _practice_completed_hours(placement)
                if (
                    placement.total_hours > 0
                    and approved_hours + payload.hours > placement.total_hours
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="Approved hours exceed placement total hours",
                    )
            now = datetime.now(timezone.utc)
            item = PracticeDiaryEntry(
                placement_id=placement.id,
                entry_date=payload.entry_date,
                hours=payload.hours,
                activity=activity,
                outcome=payload.outcome,
                supervisor_comment=payload.supervisor_comment,
                status=payload.status,
                submitted_at=(
                    now if payload.status in {"submitted", "approved"} else None
                ),
                approved_at=now if payload.status == "approved" else None,
                approved_by_id=(
                    current_user.id if payload.status == "approved" else None
                ),
                profile=payload.profile,
            )
            session.add(item)
            await session.flush()
            add_audit_event(
                session,
                action="practice_diary_entry_created",
                entity_type="practice_diary_entry",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={
                    "education_level": level,
                    "placement_id": str(placement.id),
                },
            )
            await session.commit()
            await session.refresh(item)
            return _practice_diary_out(item)

        @level_router.patch(
            "/practice-diary/{entry_id}",
            response_model=PracticeDiaryEntryOut,
            summary="Изменить или утвердить запись дневника",
        )
        async def update_practice_diary_entry(
            entry_id: uuid.UUID,
            payload: PracticeDiaryEntryUpdate,
            current_user: CurrentUser,
            session: SessionDep,
            school_id: uuid.UUID | None = Query(default=None),
            _: User = Depends(program_dep),
        ):
            school = await _school_for_level(
                session, current_user, school_id, level
            )
            item = await _practice_diary_for_institution(
                session, entry_id, school.id, level
            )
            placement = await _practice_placement_for_institution(
                session, item.placement_id, school.id, level
            )
            if placement.status in {"cancelled", "archived"}:
                raise HTTPException(
                    status_code=409,
                    detail="Archived placement cannot be changed",
                )
            updates = payload.model_dump(exclude_unset=True)
            for field in (
                "entry_date",
                "hours",
                "activity",
                "status",
                "profile",
            ):
                if field in updates and updates[field] is None:
                    raise HTTPException(
                        status_code=422, detail=f"{field} cannot be empty"
                    )
            entry_date = updates.get("entry_date", item.entry_date)
            if (
                entry_date < placement.starts_on
                or entry_date > placement.ends_on
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Entry date must be inside the placement period",
                )
            if "activity" in updates:
                updates["activity"] = updates["activity"].strip()
                if not updates["activity"]:
                    raise HTTPException(
                        status_code=422, detail="Activity cannot be empty"
                    )
            new_status = updates.get("status", item.status)
            hours = float(updates.get("hours", item.hours or 0))
            now = datetime.now(timezone.utc)
            if new_status == "approved":
                other_approved = round(
                    sum(
                        float(entry.hours or 0)
                        for entry in placement.diary_entries
                        if entry.id != item.id and entry.status == "approved"
                    ),
                    2,
                )
                if (
                    placement.total_hours > 0
                    and other_approved + hours > placement.total_hours
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="Approved hours exceed placement total hours",
                    )
                item.approved_at = item.approved_at or now
                item.approved_by_id = item.approved_by_id or current_user.id
            else:
                item.approved_at = None
                item.approved_by_id = None
            if new_status in {"submitted", "approved"} and item.submitted_at is None:
                item.submitted_at = now
            for field, value in updates.items():
                setattr(item, field, value)
            add_audit_event(
                session,
                action="practice_diary_entry_updated",
                entity_type="practice_diary_entry",
                entity_id=item.id,
                school_id=school.id,
                user_id=current_user.id,
                details={"education_level": level, "fields": sorted(updates)},
            )
            await session.commit()
            await session.refresh(item)
            return _practice_diary_out(item)

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
