"""Learning-content API: subjects, topics, textbooks and courses."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep, ensure_school_access
from app.models.lms import (
    Course,
    CourseClass,
    CourseTopic,
    Lesson,
    Method,
    Subject,
    Textbook,
    TextbookTopic,
    Topic,
)
from app.schemas.lms import (
    CourseClassOut,
    CourseDetailOut,
    CourseOut,
    CourseTopicOut,
    LessonOut,
    MethodOut,
    SubjectOut,
    TextbookDetailOut,
    TextbookLinkOut,
    TextbookList,
    TextbookOut,
    TextbookTopicOut,
    TopicDetailOut,
    TopicList,
    TopicOut,
)

router = APIRouter(prefix="/lms", tags=["lms"])


@router.get("/subjects", response_model=list[SubjectOut], summary="Предметы")
async def list_subjects(current_user: CurrentUser, session: SessionDep):
    stmt = (
        select(Subject)
        .where(Subject.is_active.is_(True))
        .order_by(Subject.order_index, Subject.name)
    )
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectOut,
    summary="Карточка предмета",
)
async def get_subject(
    subject_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    subject = await session.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get("/topics", response_model=TopicList, summary="Каталог тем")
async def list_topics(
    current_user: CurrentUser,
    session: SessionDep,
    subject_id: uuid.UUID | None = Query(default=None),
    grade: int | None = Query(default=None, ge=1, le=11),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = [Topic.status == "active"]
    if subject_id is not None:
        conditions.append(Topic.subject_id == subject_id)
    if grade is not None:
        conditions.append(Topic.class_number == grade)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Topic.title.ilike(pattern),
                Topic.code.ilike(pattern),
                Topic.description.ilike(pattern),
            )
        )

    total = (
        await session.execute(
            select(func.count()).select_from(Topic).where(*conditions)
        )
    ).scalar_one()
    items = (
        await session.execute(
            select(Topic)
            .where(*conditions)
            .order_by(Topic.subject_id, Topic.class_number, Topic.order_index, Topic.title)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return TopicList(
        items=[TopicOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/topics/by-code/{code}",
    response_model=TopicDetailOut,
    summary="Тема по коду",
)
async def get_topic_by_code(
    code: str,
    current_user: CurrentUser,
    session: SessionDep,
):
    topic = (
        await session.execute(select(Topic).where(Topic.code == code))
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return await _topic_detail(topic, session)


@router.get(
    "/topics/{topic_id}",
    response_model=TopicDetailOut,
    summary="Карточка темы",
)
async def get_topic(
    topic_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    topic = await session.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return await _topic_detail(topic, session)


async def _topic_detail(topic: Topic, session: AsyncSession) -> TopicDetailOut:
    methods = (
        await session.execute(
            select(Method)
            .where(Method.topic_id == topic.id)
            .order_by(Method.order_index, Method.name)
        )
    ).scalars().all()
    lessons = (
        await session.execute(
            select(Lesson)
            .where(Lesson.topic_id == topic.id)
            .order_by(Lesson.order_index, Lesson.title)
        )
    ).scalars().all()
    links = (
        await session.execute(
            select(TextbookTopic, Textbook)
            .join(Textbook, Textbook.id == TextbookTopic.textbook_id)
            .where(TextbookTopic.topic_id == topic.id)
            .order_by(Textbook.class_number, Textbook.title)
        )
    ).all()

    payload = TopicOut.model_validate(topic).model_dump()
    payload["methods"] = [MethodOut.model_validate(item) for item in methods]
    payload["lessons"] = [LessonOut.model_validate(item) for item in lessons]
    payload["textbooks"] = [
        TextbookLinkOut(
            id=book.id,
            title=book.title,
            author=book.author,
            pages=book.pages,
            file_id=book.file_id,
            page_from=link.page_from,
            page_to=link.page_to,
        )
        for link, book in links
    ]
    return TopicDetailOut(**payload)


@router.get("/textbooks", response_model=TextbookList, summary="Учебники")
async def list_textbooks(
    current_user: CurrentUser,
    session: SessionDep,
    subject_id: uuid.UUID | None = Query(default=None),
    grade: int | None = Query(default=None, ge=1, le=11),
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = [Textbook.status == "active"]
    if subject_id is not None:
        conditions.append(Textbook.subject_id == subject_id)
    if grade is not None:
        conditions.append(Textbook.class_number == grade)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Textbook.title.ilike(pattern),
                Textbook.author.ilike(pattern),
                Textbook.description.ilike(pattern),
            )
        )

    total = (
        await session.execute(
            select(func.count()).select_from(Textbook).where(*conditions)
        )
    ).scalar_one()
    items = (
        await session.execute(
            select(Textbook)
            .where(*conditions)
            .order_by(Textbook.class_number, Textbook.title)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return TextbookList(
        items=[TextbookOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/textbooks/{textbook_id}",
    response_model=TextbookDetailOut,
    summary="Карточка учебника",
)
async def get_textbook(
    textbook_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    textbook = await session.get(Textbook, textbook_id)
    if textbook is None:
        raise HTTPException(status_code=404, detail="Textbook not found")
    links = (
        await session.execute(
            select(TextbookTopic, Topic)
            .join(Topic, Topic.id == TextbookTopic.topic_id)
            .where(TextbookTopic.textbook_id == textbook_id)
            .order_by(Topic.order_index, Topic.title)
        )
    ).all()
    payload = TextbookOut.model_validate(textbook).model_dump()
    payload["topics"] = [
        TextbookTopicOut(
            topic_id=topic.id,
            topic_code=topic.code,
            topic_title=topic.title,
            page_from=link.page_from,
            page_to=link.page_to,
        )
        for link, topic in links
    ]
    return TextbookDetailOut(**payload)


@router.get("/courses", response_model=list[CourseOut], summary="Курсы школы")
async def list_courses(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    grade: int | None = Query(default=None, ge=1, le=11),
    mine: bool = Query(default=False, description="Только курсы текущего учителя"),
):
    tenant_id = ensure_school_access(current_user, school_id)
    conditions = [Course.school_id == tenant_id, Course.is_active.is_(True)]
    if subject_id is not None:
        conditions.append(Course.subject_id == subject_id)
    if grade is not None:
        conditions.append(Course.grade == grade)
    if mine and current_user.role == "teacher":
        conditions.append(Course.teacher_id == current_user.id)
    stmt = (
        select(Course)
        .where(*conditions)
        .order_by(Course.grade, Course.title)
    )
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetailOut,
    summary="Карточка курса",
)
async def get_course(
    course_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)
    course = (
        await session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(
                selectinload(Course.topic_links).selectinload(CourseTopic.topic),
                selectinload(Course.class_links).selectinload(CourseClass.school_class),
            )
        )
    ).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.school_id is not None and course.school_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access is forbidden")

    payload = CourseOut.model_validate(course).model_dump()
    payload["topics"] = [
        CourseTopicOut(
            topic_id=link.topic.id,
            code=link.topic.code,
            title=link.topic.title,
            order_index=link.order_index,
            enabled=link.enabled,
        )
        for link in course.topic_links
        if link.topic is not None
    ]
    payload["classes"] = [
        CourseClassOut(
            class_id=link.school_class.id,
            title=link.school_class.title,
            grade=link.school_class.grade,
            letter=link.school_class.letter,
        )
        for link in course.class_links
        if link.school_class is not None
    ]
    return CourseDetailOut(**payload)
