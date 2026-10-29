"""Journal API: schedule, grades, attendance and summaries."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep, ensure_school_access
from app.models.iam import User, UserRelation
from app.models.journal import JournalEntry, LessonSchedule
from app.models.lms import Subject, Topic
from app.models.org import ClassMembership, SchoolClass, TeacherSubject
from app.schemas.journal import (
    JournalBulkIn,
    JournalBulkOut,
    JournalClassOut,
    JournalEntryIn,
    JournalEntryOut,
    JournalEntryUpdate,
    JournalStudentOut,
    JournalSummaryListOut,
    JournalSummaryOut,
    ScheduleItemIn,
    ScheduleItemOut,
    ScheduleItemUpdate,
    ScheduleListOut,
    StatusOut,
)

router = APIRouter(prefix="/journal", tags=["journal"])

WEEKDAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]
ATTENDANCE_VALUES = ("present", "absent", "sick", "late", "excused")
TEACHER_ROLES = {"superadmin", "admin", "methodologist", "teacher"}
STAFF_ROLES = TEACHER_ROLES | {"psychologist", "secretary"}


def _ensure_role(user: User, roles: set[str]) -> None:
    if user.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _schedule_stmt():
    return select(LessonSchedule).options(
        selectinload(LessonSchedule.school_class),
        selectinload(LessonSchedule.subject),
        selectinload(LessonSchedule.teacher),
        selectinload(LessonSchedule.topic),
    )


def _entry_stmt():
    return select(JournalEntry).options(
        selectinload(JournalEntry.school_class),
        selectinload(JournalEntry.subject),
        selectinload(JournalEntry.teacher),
        selectinload(JournalEntry.student),
    )


def _schedule_out(item: LessonSchedule) -> ScheduleItemOut:
    return ScheduleItemOut(
        id=item.id,
        school_id=item.school_id,
        class_id=item.class_id,
        class_name=item.school_class.display_name if item.school_class else None,
        subject_id=item.subject_id,
        subject_name=item.subject.name if item.subject else None,
        subject_icon=item.subject.icon if item.subject else None,
        teacher_id=item.teacher_id,
        teacher_name=item.teacher.full_name if item.teacher else None,
        day_of_week=item.day_of_week,
        lesson_no=item.lesson_no,
        start_time=item.start_time,
        end_time=item.end_time,
        room=item.room,
        topic_id=item.topic_id,
        topic_title=item.topic.title if item.topic else None,
        note=item.note,
        valid_from=item.valid_from,
        valid_to=item.valid_to,
        created_at=item.created_at,
    )


def _entry_out(entry: JournalEntry) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        school_id=entry.school_id,
        class_id=entry.class_id,
        class_name=entry.school_class.display_name if entry.school_class else None,
        subject_id=entry.subject_id,
        subject_name=entry.subject.name if entry.subject else None,
        teacher_id=entry.teacher_id,
        teacher_name=entry.teacher.full_name if entry.teacher else None,
        student_id=entry.student_id,
        student_name=entry.student.full_name if entry.student else None,
        lesson_date=entry.lesson_date,
        lesson_topic=entry.lesson_topic,
        grade=entry.grade,
        attendance=entry.attendance,
        comment=entry.comment,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def _class_scope(
    session: AsyncSession, tenant_id: uuid.UUID, class_id: uuid.UUID
) -> SchoolClass:
    school_class = await session.get(SchoolClass, class_id)
    if school_class is None or school_class.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Class not found")
    if school_class.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Class belongs to another school")
    return school_class


async def _subject_or_404(session: AsyncSession, subject_id: uuid.UUID) -> Subject:
    subject = await session.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


async def _student_class_ids(
    session: AsyncSession, student_id: uuid.UUID
) -> set[uuid.UUID]:
    stmt = select(ClassMembership.class_id).where(
        ClassMembership.user_id == student_id,
        ClassMembership.left_at.is_(None),
    )
    return set((await session.execute(stmt)).scalars().all())


async def _child_ids(session: AsyncSession, parent_id: uuid.UUID) -> set[uuid.UUID]:
    stmt = select(UserRelation.child_id).where(UserRelation.parent_id == parent_id)
    return set((await session.execute(stmt)).scalars().all())


async def _teacher_class_ids(
    session: AsyncSession, teacher_id: uuid.UUID
) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    stmt = select(TeacherSubject.class_id).where(
        TeacherSubject.teacher_id == teacher_id,
        TeacherSubject.class_id.is_not(None),
    )
    ids |= set((await session.execute(stmt)).scalars().all())
    stmt = select(LessonSchedule.class_id).where(
        LessonSchedule.teacher_id == teacher_id
    )
    ids |= set((await session.execute(stmt)).scalars().all())
    stmt = select(SchoolClass.id).where(
        SchoolClass.homeroom_teacher_id == teacher_id,
        SchoolClass.deleted_at.is_(None),
    )
    ids |= set((await session.execute(stmt)).scalars().all())
    return ids


async def _ensure_staff_can_edit_class(
    session: AsyncSession, user: User, class_id: uuid.UUID
) -> None:
    if user.role in {"superadmin", "admin", "methodologist"}:
        return
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    class_ids = await _teacher_class_ids(session, user.id)
    if class_id not in class_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This class is not assigned to the teacher",
        )


async def _student_in_class(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    class_id: uuid.UUID,
    student_id: uuid.UUID,
) -> User:
    student = await session.get(User, student_id)
    if (
        student is None
        or student.role != "student"
        or student.deleted_at is not None
    ):
        raise HTTPException(status_code=404, detail="Student not found")
    if student.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Student belongs to another school")
    membership = (
        await session.execute(
            select(ClassMembership).where(
                ClassMembership.class_id == class_id,
                ClassMembership.user_id == student_id,
                ClassMembership.left_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=400, detail="Student is not a member of the class"
        )
    return student


async def _teacher_for_schedule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    teacher_id: uuid.UUID | None,
    current_user: User,
) -> User | None:
    if current_user.role == "teacher":
        return current_user
    if teacher_id is None:
        return None
    teacher = await session.get(User, teacher_id)
    if teacher is None or teacher.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if teacher.role not in TEACHER_ROLES:
        raise HTTPException(status_code=400, detail="User is not a teacher")
    if teacher.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Teacher belongs to another school")
    return teacher


async def _apply_schedule_links(
    session: AsyncSession,
    item: LessonSchedule,
    *,
    tenant_id: uuid.UUID,
    class_id: uuid.UUID,
    subject_id: uuid.UUID,
    teacher_id: uuid.UUID | None,
    topic_id: uuid.UUID | None,
    current_user: User,
) -> None:
    school_class = await _class_scope(session, tenant_id, class_id)
    subject = await _subject_or_404(session, subject_id)
    teacher = await _teacher_for_schedule(
        session, tenant_id, teacher_id, current_user
    )
    topic = None
    if topic_id is not None:
        topic = await session.get(Topic, topic_id)
        if topic is None:
            raise HTTPException(status_code=404, detail="Topic not found")
        if topic.subject_id != subject.id:
            raise HTTPException(
                status_code=400, detail="Topic belongs to another subject"
            )
    item.school_id = tenant_id
    item.class_id = class_id
    item.school_class = school_class
    item.subject_id = subject_id
    item.subject = subject
    item.teacher_id = teacher.id if teacher else None
    item.teacher = teacher
    item.topic_id = topic.id if topic else None
    item.topic = topic


# ------------------------------------------------------------------- classes
@router.get(
    "/classes",
    response_model=list[JournalClassOut],
    summary="Классы, доступные в журнале",
)
async def list_journal_classes(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(
        default=None, description="Required for a parent request"
    ),
):
    tenant_id = ensure_school_access(current_user, school_id)
    ids: set[uuid.UUID] | None = None

    if current_user.role == "teacher":
        ids = await _teacher_class_ids(session, current_user.id)
        if not ids:
            return []
    elif current_user.role == "student":
        ids = await _student_class_ids(session, current_user.id)
        if not ids:
            return []
    elif current_user.role == "parent":
        if student_id is None:
            raise HTTPException(
                status_code=400, detail="student_id is required for a parent request"
            )
        children = await _child_ids(session, current_user.id)
        if student_id not in children:
            raise HTTPException(
                status_code=403, detail="Student is not linked to this parent"
            )
        ids = await _student_class_ids(session, student_id)
        if not ids:
            return []
    elif current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    stmt = select(SchoolClass).where(
        SchoolClass.school_id == tenant_id,
        SchoolClass.deleted_at.is_(None),
    )
    if ids is not None:
        stmt = stmt.where(SchoolClass.id.in_(ids))
    stmt = stmt.order_by(SchoolClass.grade, SchoolClass.letter)
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/classes/{class_id}/students",
    response_model=list[JournalStudentOut],
    summary="Ученики класса для журнала",
)
async def list_class_students(
    class_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, STAFF_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    await _class_scope(session, tenant_id, class_id)
    if current_user.role == "teacher":
        await _ensure_staff_can_edit_class(session, current_user, class_id)

    stmt = (
        select(User)
        .join(ClassMembership, ClassMembership.user_id == User.id)
        .where(
            ClassMembership.class_id == class_id,
            ClassMembership.left_at.is_(None),
            User.role == "student",
            User.deleted_at.is_(None),
        )
        .order_by(User.last_name, User.first_name, User.middle_name)
    )
    return list((await session.execute(stmt)).scalars().all())


# ------------------------------------------------------------------ schedule
@router.get(
    "/schedule",
    response_model=ScheduleListOut,
    summary="Расписание",
)
async def list_schedule(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(
        default=None, description="Required for a parent request"
    ),
    on_date: date | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)
    stmt = select(LessonSchedule).where(LessonSchedule.school_id == tenant_id)

    if current_user.role == "teacher":
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            await _ensure_staff_can_edit_class(session, current_user, class_id)
            stmt = stmt.where(LessonSchedule.class_id == class_id)
        else:
            class_ids = await _teacher_class_ids(session, current_user.id)
            if class_ids:
                stmt = stmt.where(LessonSchedule.class_id.in_(class_ids))
            else:
                stmt = stmt.where(LessonSchedule.teacher_id == current_user.id)
    elif current_user.role in {"superadmin", "admin", "methodologist"}:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            stmt = stmt.where(LessonSchedule.class_id == class_id)
    elif current_user.role == "student":
        class_ids = await _student_class_ids(session, current_user.id)
        if not class_ids:
            return ScheduleListOut(weekdays=WEEKDAYS, schedule=[])
        stmt = stmt.where(LessonSchedule.class_id.in_(class_ids))
    elif current_user.role == "parent":
        if student_id is None:
            raise HTTPException(
                status_code=400, detail="student_id is required for a parent request"
            )
        children = await _child_ids(session, current_user.id)
        if student_id not in children:
            raise HTTPException(
                status_code=403, detail="Student is not linked to this parent"
            )
        class_ids = await _student_class_ids(session, student_id)
        if not class_ids:
            return ScheduleListOut(weekdays=WEEKDAYS, schedule=[])
        stmt = stmt.where(LessonSchedule.class_id.in_(class_ids))
    elif current_user.role in STAFF_ROLES:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            stmt = stmt.where(LessonSchedule.class_id == class_id)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if on_date is not None:
        stmt = stmt.where(
            LessonSchedule.valid_from <= on_date,
            or_(
                LessonSchedule.valid_to.is_(None),
                LessonSchedule.valid_to >= on_date,
            ),
        )
    stmt = stmt.options(
        selectinload(LessonSchedule.school_class),
        selectinload(LessonSchedule.subject),
        selectinload(LessonSchedule.teacher),
        selectinload(LessonSchedule.topic),
    ).order_by(LessonSchedule.day_of_week, LessonSchedule.lesson_no)
    items = list((await session.execute(stmt)).scalars().all())
    return ScheduleListOut(
        weekdays=WEEKDAYS, schedule=[_schedule_out(item) for item in items]
    )


@router.post(
    "/schedule",
    response_model=ScheduleItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить или заменить урок в расписании",
)
async def save_schedule_item(
    payload: ScheduleItemIn,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    await _class_scope(session, tenant_id, payload.class_id)
    await _ensure_staff_can_edit_class(session, current_user, payload.class_id)

    valid_from = payload.valid_from or _today()
    if payload.valid_to is not None and payload.valid_to < valid_from:
        raise HTTPException(status_code=400, detail="valid_to is before valid_from")

    existing = (
        await session.execute(
            _schedule_stmt().where(
                LessonSchedule.class_id == payload.class_id,
                LessonSchedule.day_of_week == payload.day_of_week,
                LessonSchedule.lesson_no == payload.lesson_no,
                LessonSchedule.valid_from == valid_from,
            )
        )
    ).scalar_one_or_none()

    item = existing or LessonSchedule(
        school_id=tenant_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        day_of_week=payload.day_of_week,
        lesson_no=payload.lesson_no,
        start_time=payload.start_time,
        end_time=payload.end_time,
        valid_from=valid_from,
        created_at=_now(),
    )
    await _apply_schedule_links(
        session,
        item,
        tenant_id=tenant_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
        topic_id=payload.topic_id,
        current_user=current_user,
    )
    item.day_of_week = payload.day_of_week
    item.lesson_no = payload.lesson_no
    item.start_time = payload.start_time
    item.end_time = payload.end_time
    item.room = payload.room
    item.note = payload.note
    item.valid_from = valid_from
    item.valid_to = payload.valid_to
    if existing is None:
        session.add(item)
    await session.flush()
    response = _schedule_out(item)
    await session.commit()
    return response


@router.patch(
    "/schedule/{item_id}",
    response_model=ScheduleItemOut,
    summary="Изменить урок расписания",
)
async def update_schedule_item(
    item_id: uuid.UUID,
    payload: ScheduleItemUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    item = (
        await session.execute(_schedule_stmt().where(LessonSchedule.id == item_id))
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    if item.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access is forbidden")
    await _ensure_staff_can_edit_class(session, current_user, item.class_id)

    updates = payload.model_dump(exclude_unset=True)
    required = {
        "class_id",
        "subject_id",
        "day_of_week",
        "lesson_no",
        "start_time",
        "end_time",
        "valid_from",
    }
    for field in required:
        if field in updates and updates[field] is None:
            raise HTTPException(status_code=400, detail=f"{field} cannot be null")

    class_id = updates.get("class_id", item.class_id)
    subject_id = updates.get("subject_id", item.subject_id)
    teacher_id = updates.get("teacher_id", item.teacher_id)
    topic_id = updates.get("topic_id", item.topic_id)
    if class_id != item.class_id:
        await _ensure_staff_can_edit_class(session, current_user, class_id)
    await _apply_schedule_links(
        session,
        item,
        tenant_id=tenant_id,
        class_id=class_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        topic_id=topic_id,
        current_user=current_user,
    )

    for field in ("day_of_week", "lesson_no", "start_time", "end_time", "room", "note"):
        if field in updates:
            setattr(item, field, updates[field])
    if "valid_from" in updates:
        item.valid_from = updates["valid_from"]
    if "valid_to" in updates:
        item.valid_to = updates["valid_to"]

    if item.end_time <= item.start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")
    if item.valid_to is not None and item.valid_to < item.valid_from:
        raise HTTPException(status_code=400, detail="valid_to is before valid_from")

    await session.flush()
    response = _schedule_out(item)
    await session.commit()
    return response


@router.delete(
    "/schedule/{item_id}",
    response_model=StatusOut,
    summary="Удалить урок расписания",
)
async def delete_schedule_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    item = await session.get(LessonSchedule, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule item not found")
    if item.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access is forbidden")
    await _ensure_staff_can_edit_class(session, current_user, item.class_id)
    await session.delete(item)
    await session.commit()
    return StatusOut()


# ------------------------------------------------------------------- entries
@router.get(
    "/entries",
    response_model=list[JournalEntryOut],
    summary="Записи журнала",
)
async def list_entries(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    tenant_id = ensure_school_access(current_user, school_id)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from is after date_to")
    conditions = [JournalEntry.school_id == tenant_id]

    if current_user.role == "teacher":
        class_ids = await _teacher_class_ids(session, current_user.id)
        if class_id is not None:
            if class_id not in class_ids:
                raise HTTPException(
                    status_code=403, detail="This class is not assigned to the teacher"
                )
            conditions.append(JournalEntry.class_id == class_id)
        else:
            if not class_ids:
                return []
            conditions.append(JournalEntry.class_id.in_(class_ids))
    elif current_user.role in {"superadmin", "admin", "methodologist"}:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            conditions.append(JournalEntry.class_id == class_id)
    elif current_user.role == "student":
        if student_id is not None and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access to another student")
        conditions.append(JournalEntry.student_id == current_user.id)
    elif current_user.role == "parent":
        if student_id is None:
            raise HTTPException(
                status_code=400, detail="student_id is required for a parent request"
            )
        children = await _child_ids(session, current_user.id)
        if student_id not in children:
            raise HTTPException(
                status_code=403, detail="Student is not linked to this parent"
            )
        conditions.append(JournalEntry.student_id == student_id)
    elif current_user.role in STAFF_ROLES:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            conditions.append(JournalEntry.class_id == class_id)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if subject_id is not None:
        conditions.append(JournalEntry.subject_id == subject_id)
    if student_id is not None and current_user.role in STAFF_ROLES:
        conditions.append(JournalEntry.student_id == student_id)
    if date_from is not None:
        conditions.append(JournalEntry.lesson_date >= date_from)
    if date_to is not None:
        conditions.append(JournalEntry.lesson_date <= date_to)

    stmt = (
        _entry_stmt()
        .where(*conditions)
        .order_by(JournalEntry.lesson_date.desc(), JournalEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = list((await session.execute(stmt)).scalars().all())
    return [_entry_out(entry) for entry in entries]


@router.post(
    "/entries",
    response_model=JournalEntryOut,
    summary="Выставить оценку или отметить посещаемость",
)
async def save_entry(
    payload: JournalEntryIn,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    school_class = await _class_scope(session, tenant_id, payload.class_id)
    await _ensure_staff_can_edit_class(session, current_user, payload.class_id)
    subject = await _subject_or_404(session, payload.subject_id)
    student = await _student_in_class(
        session, tenant_id, payload.class_id, payload.student_id
    )

    existing = (
        await session.execute(
            _entry_stmt().where(
                JournalEntry.class_id == payload.class_id,
                JournalEntry.subject_id == payload.subject_id,
                JournalEntry.student_id == payload.student_id,
                JournalEntry.lesson_date == payload.lesson_date,
            )
        )
    ).scalar_one_or_none()

    now = _now()
    entry = existing or JournalEntry(
        id=uuid.uuid4(),
        school_id=tenant_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=current_user.id,
        student_id=payload.student_id,
        lesson_date=payload.lesson_date,
        created_at=now,
        updated_at=now,
    )
    entry.school_id = tenant_id
    entry.class_id = payload.class_id
    entry.school_class = school_class
    entry.subject_id = payload.subject_id
    entry.subject = subject
    entry.teacher_id = current_user.id
    entry.teacher = current_user
    entry.student_id = payload.student_id
    entry.student = student
    entry.lesson_date = payload.lesson_date
    entry.lesson_topic = payload.lesson_topic
    entry.grade = payload.grade
    entry.attendance = payload.attendance
    entry.comment = payload.comment
    entry.updated_at = now
    if existing is None:
        session.add(entry)
    await session.flush()
    response = _entry_out(entry)
    await session.commit()
    return response


@router.post(
    "/entries/bulk",
    response_model=JournalBulkOut,
    summary="Массово выставить оценки и посещаемость",
)
async def save_entries_bulk(
    payload: JournalBulkIn,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    school_class = await _class_scope(session, tenant_id, payload.class_id)
    await _ensure_staff_can_edit_class(session, current_user, payload.class_id)
    subject = await _subject_or_404(session, payload.subject_id)

    student_ids = {item.student_id for item in payload.items}
    if len(student_ids) != len(payload.items):
        raise HTTPException(
            status_code=400, detail="Each student may appear only once"
        )
    students = {
        student.id: student
        for student in (
            await session.execute(
                select(User)
                .join(ClassMembership, ClassMembership.user_id == User.id)
                .where(
                    ClassMembership.class_id == payload.class_id,
                    ClassMembership.user_id.in_(student_ids),
                    ClassMembership.left_at.is_(None),
                    User.role == "student",
                    User.school_id == tenant_id,
                    User.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    }
    missing = student_ids - set(students)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Students are not members of the class: {len(missing)}",
        )

    existing_rows = list(
        (
            await session.execute(
                _entry_stmt().where(
                    JournalEntry.class_id == payload.class_id,
                    JournalEntry.subject_id == payload.subject_id,
                    JournalEntry.lesson_date == payload.lesson_date,
                    JournalEntry.student_id.in_(student_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    existing = {entry.student_id: entry for entry in existing_rows}
    now = _now()
    created = 0
    updated = 0
    output: list[JournalEntryOut] = []

    for item in payload.items:
        student = students[item.student_id]
        entry = existing.get(item.student_id)
        if entry is None:
            entry = JournalEntry(
                id=uuid.uuid4(),
                school_id=tenant_id,
                class_id=payload.class_id,
                subject_id=payload.subject_id,
                teacher_id=current_user.id,
                student_id=item.student_id,
                lesson_date=payload.lesson_date,
                created_at=now,
                updated_at=now,
            )
            session.add(entry)
            created += 1
        else:
            updated += 1
        entry.school_id = tenant_id
        entry.class_id = payload.class_id
        entry.school_class = school_class
        entry.subject_id = payload.subject_id
        entry.subject = subject
        entry.teacher_id = current_user.id
        entry.teacher = current_user
        entry.student_id = item.student_id
        entry.student = student
        entry.lesson_date = payload.lesson_date
        entry.lesson_topic = payload.lesson_topic
        entry.grade = item.grade
        entry.attendance = item.attendance
        entry.comment = item.comment
        entry.updated_at = now
        output.append(_entry_out(entry))

    await session.flush()
    await session.commit()
    return JournalBulkOut(created=created, updated=updated, entries=output)


@router.patch(
    "/entries/{entry_id}",
    response_model=JournalEntryOut,
    summary="Изменить запись журнала",
)
async def update_entry(
    entry_id: uuid.UUID,
    payload: JournalEntryUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    entry = (
        await session.execute(_entry_stmt().where(JournalEntry.id == entry_id))
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    if entry.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access is forbidden")
    await _ensure_staff_can_edit_class(session, current_user, entry.class_id)

    updates = payload.model_dump(exclude_unset=True)
    if "attendance" in updates and updates["attendance"] is None:
        raise HTTPException(status_code=400, detail="attendance cannot be null")
    for field, value in updates.items():
        setattr(entry, field, value)
    entry.updated_at = _now()
    await session.flush()
    response = _entry_out(entry)
    await session.commit()
    return response


@router.delete(
    "/entries/{entry_id}",
    response_model=StatusOut,
    summary="Удалить запись журнала",
)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    entry = await session.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    if entry.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access is forbidden")
    await _ensure_staff_can_edit_class(session, current_user, entry.class_id)
    await session.delete(entry)
    await session.commit()
    return StatusOut()


@router.get(
    "/summary",
    response_model=JournalSummaryListOut,
    summary="Сводка оценок и посещаемости",
)
async def journal_summary(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from is after date_to")
    conditions: list[Any] = [JournalEntry.school_id == tenant_id]

    if current_user.role == "teacher":
        class_ids = await _teacher_class_ids(session, current_user.id)
        if class_id is not None:
            if class_id not in class_ids:
                raise HTTPException(
                    status_code=403, detail="This class is not assigned to the teacher"
                )
            conditions.append(JournalEntry.class_id == class_id)
        else:
            if not class_ids:
                return JournalSummaryListOut()
            conditions.append(JournalEntry.class_id.in_(class_ids))
    elif current_user.role in {"superadmin", "admin", "methodologist"}:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            conditions.append(JournalEntry.class_id == class_id)
    elif current_user.role == "student":
        if student_id is not None and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access to another student")
        conditions.append(JournalEntry.student_id == current_user.id)
    elif current_user.role == "parent":
        if student_id is None:
            raise HTTPException(
                status_code=400, detail="student_id is required for a parent request"
            )
        children = await _child_ids(session, current_user.id)
        if student_id not in children:
            raise HTTPException(
                status_code=403, detail="Student is not linked to this parent"
            )
        conditions.append(JournalEntry.student_id == student_id)
    elif current_user.role in STAFF_ROLES:
        if class_id is not None:
            await _class_scope(session, tenant_id, class_id)
            conditions.append(JournalEntry.class_id == class_id)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if subject_id is not None:
        conditions.append(JournalEntry.subject_id == subject_id)
    if student_id is not None and current_user.role in STAFF_ROLES:
        conditions.append(JournalEntry.student_id == student_id)
    if date_from is not None:
        conditions.append(JournalEntry.lesson_date >= date_from)
    if date_to is not None:
        conditions.append(JournalEntry.lesson_date <= date_to)

    entries = list(
        (
            await session.execute(
                select(JournalEntry)
                .options(selectinload(JournalEntry.student))
                .where(*conditions)
                .order_by(JournalEntry.lesson_date, JournalEntry.created_at)
            )
        )
        .scalars()
        .all()
    )
    grouped: dict[uuid.UUID, list[JournalEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.student_id, []).append(entry)

    items: list[JournalSummaryOut] = []
    for student_id_value, student_entries in grouped.items():
        grades = [entry.grade for entry in student_entries if entry.grade is not None]
        attendance = {value: 0 for value in ATTENDANCE_VALUES}
        for entry in student_entries:
            attendance[entry.attendance] = attendance.get(entry.attendance, 0) + 1
        student = student_entries[0].student
        items.append(
            JournalSummaryOut(
                student_id=student_id_value,
                student_name=student.full_name if student else "",
                entries_count=len(student_entries),
                grades_count=len(grades),
                average_grade=(
                    round(sum(grades) / len(grades), 2) if grades else None
                ),
                attendance=attendance,
                grades=grades,
            )
        )
    items.sort(key=lambda item: item.student_name)
    return JournalSummaryListOut(items=items)
