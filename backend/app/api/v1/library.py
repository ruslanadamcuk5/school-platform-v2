"""Library API: books, class access and recommendations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep, ensure_school_access
from app.models.iam import User, UserRelation
from app.models.journal import LessonSchedule
from app.models.lms import (
    LibraryItem,
    LibraryItemClass,
    LibraryRecommendation,
    LibraryRecommendationStatus,
    Subject,
    Textbook,
    TextbookTopic,
)
from app.models.org import ClassMembership, SchoolClass, TeacherSubject
from app.schemas.library import (
    LibraryBookCreate,
    LibraryBookDetailOut,
    LibraryBookOut,
    LibraryBookUpdate,
    LibraryCatalogItemOut,
    LibraryCatalogOut,
    LibraryCatalogTopicOut,
    LibraryChildOut,
    LibraryClassOut,
    LibraryManageOut,
    LibraryOut,
    LibraryRecommendationCreate,
    LibraryRecommendationListOut,
    LibraryRecommendationOut,
    LibraryRecommendResult,
    LibraryStatsOut,
    LibraryStatusOut,
    LibraryStudentOut,
    LibraryTopicOut,
)

router = APIRouter(prefix="/library", tags=["library"])

TEACHER_ROLES = {"superadmin", "admin", "methodologist", "teacher"}
STAFF_ROLES = TEACHER_ROLES | {"psychologist", "secretary"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_role(user: User, roles: set[str]) -> None:
    if user.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _book_options():
    return (
        selectinload(LibraryItem.owner),
        selectinload(LibraryItem.subject),
        selectinload(LibraryItem.textbook)
        .selectinload(Textbook.topic_links)
        .selectinload(TextbookTopic.topic),
        selectinload(LibraryItem.class_links).selectinload(
            LibraryItemClass.school_class
        ),
    )


def _book_stmt():
    return select(LibraryItem).options(*_book_options())


def _rec_options():
    return (
        selectinload(LibraryRecommendation.book).selectinload(
            LibraryItem.textbook
        ),
        selectinload(LibraryRecommendation.topic),
        selectinload(LibraryRecommendation.teacher),
        selectinload(LibraryRecommendation.student),
        selectinload(LibraryRecommendation.school_class),
    )


def _rec_stmt():
    return select(LibraryRecommendation).options(*_rec_options())


def _topics_out(book: LibraryItem) -> list[LibraryTopicOut]:
    if book.textbook is None:
        return []
    items: list[LibraryTopicOut] = []
    for link in book.textbook.topic_links:
        topic = link.topic
        if topic is None:
            continue
        items.append(
            LibraryTopicOut(
                topic_id=topic.id,
                code=topic.code,
                title=topic.title,
                icon=topic.icon,
                class_number=topic.class_number,
                page_from=link.page_from,
                page_to=link.page_to,
            )
        )
    items.sort(key=lambda item: (item.page_from or 0, item.title))
    return items


def _book_out(book: LibraryItem) -> LibraryBookOut:
    topics_count = (
        len(book.textbook.topic_links) if book.textbook is not None else 0
    )
    return LibraryBookOut(
        id=book.id,
        title=book.title,
        author=book.author,
        description=book.description,
        class_number=book.class_number,
        subject_id=book.subject_id,
        subject_name=book.subject.name if book.subject else None,
        subject_icon=book.subject.icon if book.subject else None,
        textbook_id=book.textbook_id,
        textbook_title=book.textbook.title if book.textbook else None,
        pages=book.textbook.pages if book.textbook else None,
        topics_count=topics_count,
        classes_count=len(book.class_links),
        owner_id=book.owner_id,
        owner_name=book.owner.full_name if book.owner else None,
        class_ids=[link.class_id for link in book.class_links],
        created_at=book.created_at,
    )


def _book_detail_out(
    book: LibraryItem,
    recommendations: list[LibraryRecommendationOut] | None = None,
    manageable: bool = False,
) -> LibraryBookDetailOut:
    base = _book_out(book)
    return LibraryBookDetailOut(
        **base.model_dump(),
        topics=_topics_out(book),
        recommendations=recommendations or [],
        manageable=manageable,
    )


def _rec_out(
    rec: LibraryRecommendation,
    *,
    done_map: dict[uuid.UUID, datetime] | None = None,
    done_counts: dict[uuid.UUID, int] | None = None,
    member_counts: dict[uuid.UUID, int] | None = None,
) -> LibraryRecommendationOut:
    done_map = done_map or {}
    done_counts = done_counts or {}
    member_counts = member_counts or {}
    done_at = done_map.get(rec.id)
    total_count = (
        member_counts.get(rec.class_id, 0)
        if rec.target_type == "class" and rec.class_id is not None
        else 1
    )
    return LibraryRecommendationOut(
        id=rec.id,
        book_id=rec.book_id,
        book_title=rec.book.title if rec.book else None,
        topic_id=rec.topic_id,
        topic_title=rec.topic.title if rec.topic else None,
        teacher_id=rec.teacher_id,
        teacher_name=rec.teacher.full_name if rec.teacher else None,
        target_type=rec.target_type,
        class_id=rec.class_id,
        class_name=(
            rec.school_class.display_name if rec.school_class else None
        ),
        student_id=rec.student_id,
        student_name=rec.student.full_name if rec.student else None,
        note=rec.note,
        created_at=rec.created_at,
        done=done_at is not None,
        done_at=done_at,
        done_count=done_counts.get(rec.id, 0),
        total_count=total_count,
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


async def _student_class_ids(
    session: AsyncSession, student_id: uuid.UUID
) -> set[uuid.UUID]:
    stmt = select(ClassMembership.class_id).where(
        ClassMembership.user_id == student_id,
        ClassMembership.left_at.is_(None),
    )
    return set((await session.execute(stmt)).scalars().all())


async def _children(session: AsyncSession, parent_id: uuid.UUID) -> list[User]:
    stmt = (
        select(User)
        .join(UserRelation, UserRelation.child_id == User.id)
        .where(
            UserRelation.parent_id == parent_id,
            User.role == "student",
            User.deleted_at.is_(None),
        )
        .order_by(User.last_name, User.first_name, User.middle_name)
    )
    return list((await session.execute(stmt)).scalars().all())


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


async def _classes_for_user(
    session: AsyncSession,
    user: User,
    tenant_id: uuid.UUID,
    class_ids: list[uuid.UUID],
) -> list[SchoolClass]:
    unique = list(dict.fromkeys(class_ids))
    if not unique:
        return []
    if user.role == "teacher":
        allowed = await _teacher_class_ids(session, user.id)
        if not set(unique) <= allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Class is not assigned to the teacher",
            )
    elif user.role not in {"superadmin", "admin", "methodologist"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    classes: list[SchoolClass] = []
    for class_id in unique:
        classes.append(await _class_scope(session, tenant_id, class_id))
    return classes


async def _students_for_user(
    session: AsyncSession,
    user: User,
    tenant_id: uuid.UUID,
    student_ids: list[uuid.UUID],
) -> list[User]:
    unique = list(dict.fromkeys(student_ids))
    if not unique:
        return []
    stmt = select(User).where(
        User.id.in_(unique),
        User.role == "student",
        User.school_id == tenant_id,
        User.deleted_at.is_(None),
    )
    if user.role == "teacher":
        class_ids = await _teacher_class_ids(session, user.id)
        if not class_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No classes assigned to the teacher",
            )
        stmt = stmt.join(
            ClassMembership, ClassMembership.user_id == User.id
        ).where(
            ClassMembership.class_id.in_(class_ids),
            ClassMembership.left_at.is_(None),
        )
    elif user.role not in {"superadmin", "admin", "methodologist"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    students = list((await session.execute(stmt)).scalars().unique().all())
    if len(students) != len(unique):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student is not available to the teacher",
        )
    return students


async def _book_in_school(
    session: AsyncSession, tenant_id: uuid.UUID, book: LibraryItem
) -> bool:
    if book.owner is not None and book.owner.school_id == tenant_id:
        return True
    return any(
        link.school_class is not None
        and link.school_class.school_id == tenant_id
        for link in book.class_links
    )


async def _managed(
    session: AsyncSession, user: User, tenant_id: uuid.UUID, book: LibraryItem
) -> bool:
    if user.role in {"superadmin", "admin", "methodologist"}:
        return await _book_in_school(session, tenant_id, book)
    return book.owner_id == user.id


async def _can_access_book(
    session: AsyncSession,
    user: User,
    tenant_id: uuid.UUID,
    book: LibraryItem,
    parent_student_id: uuid.UUID | None = None,
) -> bool:
    if user.role in {"superadmin", "admin", "methodologist"}:
        return await _book_in_school(session, tenant_id, book)
    if user.role == "teacher":
        if book.owner_id == user.id:
            return True
        return any(
            link.school_class is not None
            and link.school_class.homeroom_teacher_id == user.id
            for link in book.class_links
        )
    if user.role == "student":
        class_ids = await _student_class_ids(session, user.id)
        if any(link.class_id in class_ids for link in book.class_links):
            return True
        conditions = [
            LibraryRecommendation.book_id == book.id,
            or_(
                LibraryRecommendation.student_id == user.id,
                LibraryRecommendation.class_id.in_(class_ids)
                if class_ids
                else LibraryRecommendation.class_id.is_(None),
            ),
        ]
        rec = (
            await session.execute(
                select(LibraryRecommendation.id).where(*conditions).limit(1)
            )
        ).scalar_one_or_none()
        return rec is not None
    if user.role == "parent":
        children = await _children(session, user.id)
        if parent_student_id is not None:
            children = [child for child in children if child.id == parent_student_id]
        for child in children:
            class_ids = await _student_class_ids(session, child.id)
            if any(link.class_id in class_ids for link in book.class_links):
                return True
            if class_ids:
                rec = (
                    await session.execute(
                        select(LibraryRecommendation.id)
                        .where(
                            LibraryRecommendation.book_id == book.id,
                            or_(
                                LibraryRecommendation.student_id == child.id,
                                LibraryRecommendation.class_id.in_(class_ids),
                            ),
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if rec is not None:
                    return True
        return False
    return False


async def _load_book(session: AsyncSession, book_id: uuid.UUID) -> LibraryItem:
    book = (
        await session.execute(_book_stmt().where(LibraryItem.id == book_id))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


async def _load_recommendation(
    session: AsyncSession, rec_id: uuid.UUID
) -> LibraryRecommendation:
    rec = (
        await session.execute(_rec_stmt().where(LibraryRecommendation.id == rec_id))
    ).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


async def _books_for_user(
    session: AsyncSession,
    user: User,
    tenant_id: uuid.UUID,
    *,
    class_ids: set[uuid.UUID] | None = None,
    search: str | None = None,
    class_number: int | None = None,
    subject_id: uuid.UUID | None = None,
) -> list[LibraryItem]:
    stmt = _book_stmt()
    if user.role == "teacher":
        stmt = stmt.where(LibraryItem.owner_id == user.id)
    elif user.role in {"superadmin", "admin", "methodologist"}:
        owner_ids = select(User.id).where(User.school_id == tenant_id)
        school_classes = select(SchoolClass.id).where(
            SchoolClass.school_id == tenant_id
        )
        book_ids = select(LibraryItemClass.book_id).where(
            LibraryItemClass.class_id.in_(school_classes)
        )
        stmt = stmt.where(
            or_(
                LibraryItem.owner_id.in_(owner_ids),
                LibraryItem.id.in_(book_ids),
            )
        )
    else:
        if not class_ids:
            return []
        book_ids = select(LibraryItemClass.book_id).where(
            LibraryItemClass.class_id.in_(class_ids)
        )
        stmt = stmt.where(LibraryItem.id.in_(book_ids))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                LibraryItem.title.ilike(pattern),
                LibraryItem.author.ilike(pattern),
                LibraryItem.description.ilike(pattern),
            )
        )
    if class_number is not None:
        stmt = stmt.where(LibraryItem.class_number == class_number)
    if subject_id is not None:
        stmt = stmt.where(LibraryItem.subject_id == subject_id)
    stmt = stmt.order_by(LibraryItem.title)
    return list((await session.execute(stmt)).scalars().all())


async def _student_recommendations(
    session: AsyncSession,
    student_id: uuid.UUID,
    *,
    book_id: uuid.UUID | None = None,
) -> list[LibraryRecommendationOut]:
    class_ids = await _student_class_ids(session, student_id)
    conditions: list[Any] = [
        or_(
            LibraryRecommendation.student_id == student_id,
            LibraryRecommendation.class_id.in_(class_ids)
            if class_ids
            else LibraryRecommendation.class_id.is_(None),
        )
    ]
    if book_id is not None:
        conditions.append(LibraryRecommendation.book_id == book_id)
    recs = list(
        (
            await session.execute(
                _rec_stmt()
                .where(*conditions)
                .order_by(LibraryRecommendation.created_at.desc())
            )
        )
        .scalars()
        .unique()
        .all()
    )
    if not recs:
        return []
    ids = [rec.id for rec in recs]
    rows = (
        await session.execute(
            select(
                LibraryRecommendationStatus.recommendation_id,
                LibraryRecommendationStatus.done_at,
            ).where(
                LibraryRecommendationStatus.student_id == student_id,
                LibraryRecommendationStatus.recommendation_id.in_(ids),
            )
        )
    ).all()
    done_map = {row[0]: row[1] for row in rows}
    recs.sort(key=lambda rec: (rec.id in done_map, -rec.created_at.timestamp()))
    return [_rec_out(rec, done_map=done_map) for rec in recs]


async def _sent_recommendations(
    session: AsyncSession,
    user: User,
    tenant_id: uuid.UUID,
    *,
    book_id: uuid.UUID | None = None,
    limit: int = 200,
) -> list[LibraryRecommendationOut]:
    stmt = _rec_stmt()
    if user.role == "teacher":
        stmt = stmt.where(LibraryRecommendation.teacher_id == user.id)
    elif user.role in {"superadmin", "admin", "methodologist"}:
        teacher_ids = select(User.id).where(User.school_id == tenant_id)
        stmt = stmt.where(LibraryRecommendation.teacher_id.in_(teacher_ids))
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if book_id is not None:
        stmt = stmt.where(LibraryRecommendation.book_id == book_id)
    stmt = stmt.order_by(LibraryRecommendation.created_at.desc()).limit(limit)
    recs = list((await session.execute(stmt)).scalars().unique().all())
    if not recs:
        return []
    ids = [rec.id for rec in recs]
    done_rows = (
        await session.execute(
            select(
                LibraryRecommendationStatus.recommendation_id,
                func.count(),
            )
            .where(LibraryRecommendationStatus.recommendation_id.in_(ids))
            .group_by(LibraryRecommendationStatus.recommendation_id)
        )
    ).all()
    done_counts = {row[0]: int(row[1]) for row in done_rows}
    class_ids = {
        rec.class_id
        for rec in recs
        if rec.target_type == "class" and rec.class_id is not None
    }
    member_counts: dict[uuid.UUID, int] = {}
    if class_ids:
        member_rows = (
            await session.execute(
                select(ClassMembership.class_id, func.count())
                .where(
                    ClassMembership.class_id.in_(class_ids),
                    ClassMembership.left_at.is_(None),
                )
                .group_by(ClassMembership.class_id)
            )
        ).all()
        member_counts = {row[0]: int(row[1]) for row in member_rows}
    return [
        _rec_out(rec, done_counts=done_counts, member_counts=member_counts)
        for rec in recs
    ]


def _child_out(child: User) -> LibraryChildOut:
    return LibraryChildOut(
        id=child.id, full_name=child.full_name, login=child.login
    )


def _student_out(
    student: User, class_id: uuid.UUID, class_name: str
) -> LibraryStudentOut:
    return LibraryStudentOut(
        id=student.id,
        full_name=student.full_name,
        login=student.login,
        class_id=class_id,
        class_name=class_name,
    )


def _stats_for_books(
    books: list[LibraryItem], recommendations: int = 0
) -> LibraryStatsOut:
    class_ids = {
        link.class_id for book in books for link in book.class_links
    }
    return LibraryStatsOut(
        books=len(books),
        classes=len(class_ids),
        recommendations=recommendations,
    )


# --------------------------------------------------------------------- browse
@router.get("", response_model=LibraryOut, summary="Библиотека пользователя")
async def library_home(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(
        default=None, description="Child id for a parent request"
    ),
    search: str | None = Query(default=None, max_length=255),
    class_number: int | None = Query(default=None, ge=1, le=11),
    subject_id: uuid.UUID | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)

    if current_user.role == "student":
        class_ids = await _student_class_ids(session, current_user.id)
        books = await _books_for_user(
            session,
            current_user,
            tenant_id,
            class_ids=class_ids,
            search=search,
            class_number=class_number,
            subject_id=subject_id,
        )
        recommendations = await _student_recommendations(session, current_user.id)
        active = sum(1 for rec in recommendations if not rec.done)
        done = sum(1 for rec in recommendations if rec.done)
        return LibraryOut(
            books=[_book_out(book) for book in books],
            recommendations=recommendations,
            stats=LibraryStatsOut(
                books=len(books),
                recommendations=len(recommendations),
                active=active,
                done=done,
            ),
        )

    if current_user.role == "parent":
        children = await _children(session, current_user.id)
        if not children:
            return LibraryOut()
        child = children[0]
        if student_id is not None:
            child = next(
                (item for item in children if item.id == student_id), None
            )  # type: ignore[assignment]
            if child is None:
                raise HTTPException(
                    status_code=403,
                    detail="Student is not linked to this parent",
                )
        class_ids = await _student_class_ids(session, child.id)
        books = await _books_for_user(
            session,
            current_user,
            tenant_id,
            class_ids=class_ids,
            search=search,
            class_number=class_number,
            subject_id=subject_id,
        )
        recommendations = await _student_recommendations(session, child.id)
        active = sum(1 for rec in recommendations if not rec.done)
        done = sum(1 for rec in recommendations if rec.done)
        return LibraryOut(
            books=[_book_out(book) for book in books],
            recommendations=recommendations,
            stats=LibraryStatsOut(
                books=len(books),
                recommendations=len(recommendations),
                active=active,
                done=done,
            ),
            children=[_child_out(item) for item in children],
            child=_child_out(child),
        )

    if current_user.role == "teacher":
        books = await _books_for_user(
            session,
            current_user,
            tenant_id,
            search=search,
            class_number=class_number,
            subject_id=subject_id,
        )
        recommendations = await _sent_recommendations(
            session, current_user, tenant_id
        )
        return LibraryOut(
            books=[_book_out(book) for book in books],
            recommendations=recommendations,
            stats=_stats_for_books(books, len(recommendations)),
        )

    if current_user.role in {"superadmin", "admin", "methodologist"}:
        books = await _books_for_user(
            session,
            current_user,
            tenant_id,
            search=search,
            class_number=class_number,
            subject_id=subject_id,
        )
        recommendations = await _sent_recommendations(
            session, current_user, tenant_id
        )
        return LibraryOut(
            books=[_book_out(book) for book in books],
            recommendations=recommendations,
            stats=_stats_for_books(books, len(recommendations)),
        )

    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get(
    "/books/{book_id}",
    response_model=LibraryBookDetailOut,
    summary="Карточка книги",
)
async def library_book(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(
        default=None, description="Child id for a parent request"
    ),
):
    tenant_id = ensure_school_access(current_user, school_id)
    book = await _load_book(session, book_id)
    if not await _can_access_book(
        session, current_user, tenant_id, book, student_id
    ):
        raise HTTPException(status_code=403, detail="Book is not available")
    recommendations: list[LibraryRecommendationOut] = []
    if current_user.role == "student":
        recommendations = await _student_recommendations(
            session, current_user.id, book_id=book.id
        )
    manageable = await _managed(session, current_user, tenant_id, book)
    return _book_detail_out(
        book, recommendations=recommendations, manageable=manageable
    )


@router.post(
    "/recommendations/{recommendation_id}/done",
    response_model=LibraryStatusOut,
    summary="Отметить рекомендацию выполненной",
)
async def mark_recommendation_done(
    recommendation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, {"student"})
    ensure_school_access(current_user, school_id)
    rec = await _load_recommendation(session, recommendation_id)
    class_ids = await _student_class_ids(session, current_user.id)
    visible = rec.student_id == current_user.id or (
        rec.class_id is not None and rec.class_id in class_ids
    )
    if not visible:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    existing = (
        await session.execute(
            select(LibraryRecommendationStatus).where(
                LibraryRecommendationStatus.recommendation_id == rec.id,
                LibraryRecommendationStatus.student_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            LibraryRecommendationStatus(
                id=uuid.uuid4(),
                recommendation_id=rec.id,
                student_id=current_user.id,
                done_at=_now(),
            )
        )
        await session.flush()
    await session.commit()
    return LibraryStatusOut()


# --------------------------------------------------------------------- teacher
@router.get(
    "/manage",
    response_model=LibraryManageOut,
    summary="Библиотека учителя: книги, классы и ученики",
)
async def manage_library(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    class_number: int | None = Query(default=None, ge=1, le=11),
    subject_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    books = await _books_for_user(
        session,
        current_user,
        tenant_id,
        search=search,
        class_number=class_number,
        subject_id=subject_id,
    )
    if current_user.role == "teacher":
        class_ids = await _teacher_class_ids(session, current_user.id)
        if class_ids:
            classes = list(
                (
                    await session.execute(
                        select(SchoolClass)
                        .where(
                            SchoolClass.id.in_(class_ids),
                            SchoolClass.school_id == tenant_id,
                            SchoolClass.deleted_at.is_(None),
                        )
                        .order_by(SchoolClass.grade, SchoolClass.letter)
                    )
                )
                .scalars()
                .all()
            )
        else:
            classes = []
    else:
        classes = list(
            (
                await session.execute(
                    select(SchoolClass)
                    .where(
                        SchoolClass.school_id == tenant_id,
                        SchoolClass.deleted_at.is_(None),
                    )
                    .order_by(SchoolClass.grade, SchoolClass.letter)
                )
            )
            .scalars()
            .all()
        )
    students: list[LibraryStudentOut] = []
    if classes:
        class_ids = [klass.id for klass in classes]
        rows = (
            await session.execute(
                select(User, ClassMembership, SchoolClass)
                .join(ClassMembership, ClassMembership.user_id == User.id)
                .join(SchoolClass, SchoolClass.id == ClassMembership.class_id)
                .where(
                    ClassMembership.class_id.in_(class_ids),
                    ClassMembership.left_at.is_(None),
                    User.role == "student",
                    User.school_id == tenant_id,
                    User.deleted_at.is_(None),
                )
                .order_by(
                    SchoolClass.grade,
                    SchoolClass.letter,
                    User.last_name,
                    User.first_name,
                )
            )
        ).all()
        students = [
            _student_out(user, school_class.id, school_class.display_name)
            for user, _membership, school_class in rows
        ]
    subjects = list(
        (
            await session.execute(
                select(Subject)
                .where(Subject.is_active.is_(True))
                .order_by(Subject.name)
            )
        )
        .scalars()
        .all()
    )
    return LibraryManageOut(
        books=[_book_out(book) for book in books],
        stats=_stats_for_books(books),
        classes=[LibraryClassOut.model_validate(klass) for klass in classes],
        students=students,
        subjects=subjects,
    )


@router.post(
    "/books",
    response_model=LibraryBookDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить пособие в библиотеку",
)
async def create_book(
    payload: LibraryBookCreate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    textbook = (
        await session.execute(
            select(Textbook)
            .options(
                selectinload(Textbook.subject),
                selectinload(Textbook.topic_links).selectinload(
                    TextbookTopic.topic
                ),
            )
            .where(Textbook.id == payload.textbook_id)
        )
    ).scalar_one_or_none()
    if textbook is None:
        raise HTTPException(status_code=404, detail="Textbook not found")
    classes = await _classes_for_user(
        session, current_user, tenant_id, payload.class_ids
    )
    subject = textbook.subject
    if payload.subject_id is not None:
        subject = await session.get(Subject, payload.subject_id)
        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

    now = _now()
    book = LibraryItem(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        textbook_id=textbook.id,
        subject_id=subject.id if subject else None,
        class_number=(
            payload.class_number
            if payload.class_number is not None
            else textbook.class_number
        ),
        title=payload.title or textbook.title,
        author=payload.author if payload.author is not None else textbook.author,
        description=(
            payload.description
            if payload.description is not None
            else textbook.description
        ),
        created_at=now,
    )
    book.owner = current_user
    book.textbook = textbook
    book.subject = subject
    book.class_links = [
        LibraryItemClass(
            id=uuid.uuid4(),
            book_id=book.id,
            class_id=klass.id,
            school_class=klass,
            item=book,
            added_at=now,
        )
        for klass in classes
    ]
    session.add(book)
    await session.flush()
    response = _book_detail_out(book, manageable=True)
    await session.commit()
    return response


@router.patch(
    "/books/{book_id}",
    response_model=LibraryBookDetailOut,
    summary="Изменить книгу и доступ классов",
)
async def update_book(
    book_id: uuid.UUID,
    payload: LibraryBookUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    book = await _load_book(session, book_id)
    if not await _managed(session, current_user, tenant_id, book):
        raise HTTPException(status_code=403, detail="This book is not yours")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is None:
        raise HTTPException(status_code=400, detail="title cannot be null")
    if "subject_id" in updates:
        subject = None
        if updates["subject_id"] is not None:
            subject = await session.get(Subject, updates["subject_id"])
            if subject is None:
                raise HTTPException(status_code=404, detail="Subject not found")
        book.subject_id = subject.id if subject else None
        book.subject = subject
    for field in ("title", "author", "description", "class_number"):
        if field in updates:
            setattr(book, field, updates[field])
    if updates.get("class_ids") is not None:
        classes = await _classes_for_user(
            session, current_user, tenant_id, updates["class_ids"]
        )
        book.class_links = [
            LibraryItemClass(
                id=uuid.uuid4(),
                book_id=book.id,
                class_id=klass.id,
                school_class=klass,
                item=book,
                added_at=_now(),
            )
            for klass in classes
        ]
    await session.flush()
    response = _book_detail_out(book, manageable=True)
    await session.commit()
    return response


@router.delete(
    "/books/{book_id}",
    response_model=LibraryStatusOut,
    summary="Удалить книгу из библиотеки",
)
async def delete_book(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    book = await _load_book(session, book_id)
    if not await _managed(session, current_user, tenant_id, book):
        raise HTTPException(status_code=403, detail="This book is not yours")
    await session.delete(book)
    await session.commit()
    return LibraryStatusOut()


@router.post(
    "/books/{book_id}/recommend",
    response_model=LibraryRecommendResult,
    summary="Порекомендовать книгу классу или ученикам",
)
async def recommend_book(
    book_id: uuid.UUID,
    payload: LibraryRecommendationCreate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    book = await _load_book(session, book_id)
    if not await _managed(session, current_user, tenant_id, book):
        raise HTTPException(status_code=403, detail="This book is not yours")

    topic = None
    if payload.topic_id is not None:
        if book.textbook is None:
            raise HTTPException(status_code=400, detail="Book has no textbook")
        link = next(
            (
                item
                for item in book.textbook.topic_links
                if item.topic_id == payload.topic_id
            ),
            None,
        )
        if link is None:
            raise HTTPException(
                status_code=400, detail="Topic does not belong to this book"
            )
        topic = link.topic

    classes = await _classes_for_user(
        session, current_user, tenant_id, payload.class_ids
    )
    students = await _students_for_user(
        session, current_user, tenant_id, payload.student_ids
    )
    existing_stmt = select(LibraryRecommendation).where(
        LibraryRecommendation.book_id == book.id
    )
    if payload.topic_id is None:
        existing_stmt = existing_stmt.where(
            LibraryRecommendation.topic_id.is_(None)
        )
    else:
        existing_stmt = existing_stmt.where(
            LibraryRecommendation.topic_id == payload.topic_id
        )
    existing = list(
        (await session.execute(existing_stmt)).scalars().all()
    )
    existing_keys = {
        (rec.target_type, rec.class_id, rec.student_id) for rec in existing
    }
    now = _now()
    created = 0
    skipped = 0
    items: list[LibraryRecommendationOut] = []

    def add_recommendation(
        target_type: str,
        *,
        class_obj: SchoolClass | None = None,
        student: User | None = None,
    ) -> None:
        nonlocal created, skipped
        key = (
            target_type,
            class_obj.id if class_obj else None,
            student.id if student else None,
        )
        if key in existing_keys:
            skipped += 1
            return
        rec = LibraryRecommendation(
            id=uuid.uuid4(),
            teacher_id=current_user.id,
            book_id=book.id,
            topic_id=topic.id if topic else None,
            target_type=target_type,
            student_id=student.id if student else None,
            class_id=class_obj.id if class_obj else None,
            note=payload.note,
            created_at=now,
        )
        rec.book = book
        rec.topic = topic
        rec.teacher = current_user
        rec.student = student
        rec.school_class = class_obj
        session.add(rec)
        existing_keys.add(key)
        created += 1
        items.append(_rec_out(rec))

    for klass in classes:
        add_recommendation("class", class_obj=klass)
    for student in students:
        add_recommendation("student", student=student)

    await session.flush()
    await session.commit()
    return LibraryRecommendResult(created=created, skipped=skipped, items=items)


@router.get(
    "/recommendations",
    response_model=LibraryRecommendationListOut,
    summary="Отправленные рекомендации",
)
async def list_recommendations(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    book_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    items = await _sent_recommendations(
        session, current_user, tenant_id, book_id=book_id, limit=limit
    )
    return LibraryRecommendationListOut(items=items)


@router.delete(
    "/recommendations/{recommendation_id}",
    response_model=LibraryStatusOut,
    summary="Отозвать рекомендацию",
)
async def revoke_recommendation(
    recommendation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    rec = await _load_recommendation(session, recommendation_id)
    if current_user.role == "teacher" and rec.teacher_id != current_user.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if current_user.role in {"superadmin", "admin", "methodologist"}:
        teacher = await session.get(User, rec.teacher_id)
        if teacher is None or teacher.school_id != tenant_id:
            raise HTTPException(status_code=404, detail="Recommendation not found")
    await session.delete(rec)
    await session.commit()
    return LibraryStatusOut()


@router.get(
    "/catalog",
    response_model=LibraryCatalogOut,
    summary="Пособия и темы для рекомендаций",
)
async def library_catalog(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    class_number: int | None = Query(default=None, ge=1, le=11),
    search: str | None = Query(default=None, max_length=255),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    stmt = (
        select(Textbook)
        .options(
            selectinload(Textbook.subject),
            selectinload(Textbook.topic_links).selectinload(TextbookTopic.topic),
        )
        .where(Textbook.status == "active")
    )
    if subject_id is not None:
        stmt = stmt.where(Textbook.subject_id == subject_id)
    if class_number is not None:
        stmt = stmt.where(Textbook.class_number == class_number)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Textbook.title.ilike(pattern),
                Textbook.author.ilike(pattern),
            )
        )
    textbooks = list(
        (await session.execute(stmt.order_by(Textbook.title))).scalars().all()
    )
    textbook_ids = [item.id for item in textbooks]
    book_map: dict[uuid.UUID, uuid.UUID] = {}
    if textbook_ids:
        book_stmt = select(LibraryItem.textbook_id, LibraryItem.id).where(
            LibraryItem.textbook_id.in_(textbook_ids)
        )
        if current_user.role == "teacher":
            book_stmt = book_stmt.where(LibraryItem.owner_id == current_user.id)
        else:
            owner_ids = select(User.id).where(User.school_id == tenant_id)
            school_classes = select(SchoolClass.id).where(
                SchoolClass.school_id == tenant_id
            )
            linked_books = select(LibraryItemClass.book_id).where(
                LibraryItemClass.class_id.in_(school_classes)
            )
            book_stmt = book_stmt.where(
                or_(
                    LibraryItem.owner_id.in_(owner_ids),
                    LibraryItem.id.in_(linked_books),
                )
            )
        rows = (await session.execute(book_stmt)).all()
        book_map = {row[0]: row[1] for row in rows}

    items: list[LibraryCatalogItemOut] = []
    for textbook in textbooks:
        topics = [
            LibraryCatalogTopicOut(
                topic_id=link.topic.id,
                code=link.topic.code,
                title=link.topic.title,
                icon=link.topic.icon,
                class_number=link.topic.class_number,
                page_from=link.page_from,
                page_to=link.page_to,
            )
            for link in textbook.topic_links
            if link.topic is not None
        ]
        if not topics:
            continue
        topics.sort(key=lambda item: (item.page_from or 0, item.title))
        items.append(
            LibraryCatalogItemOut(
                textbook_id=textbook.id,
                book_id=book_map.get(textbook.id),
                title=textbook.title,
                author=textbook.author,
                class_number=textbook.class_number,
                subject_id=textbook.subject_id,
                subject_name=(
                    textbook.subject.name if textbook.subject else None
                ),
                subject_icon=(
                    textbook.subject.icon if textbook.subject else None
                ),
                topics=topics,
            )
        )
    return LibraryCatalogOut(items=items)
