"""Assessment API: quizzes, assignments, submissions and results."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUser,
    SessionDep,
    ensure_school_access,
    require_permission,
    require_service,
)
from app.models.assessment import (
    Answer,
    AnswerOption,
    Assignment,
    Question,
    Quiz,
    Submission,
)
from app.models.iam import User, UserRelation
from app.models.lms import Subject
from app.models.org import ClassMembership, SchoolClass
from app.schemas.assessment import (
    AnswerDetail,
    AssignmentCreate,
    AssignmentDetailOut,
    AssignmentListItem,
    AssignmentOut,
    AssignmentResultsOut,
    QuestionOut,
    QuestionPublicOut,
    QuizCreate,
    QuizDetailOut,
    QuizOut,
    QuizUpdate,
    StudentAnswerIn,
    StudentResultOut,
    SubmissionCreate,
    SubmissionOut,
    SubmissionResultOut,
)
from app.services.grading import answer_detail, summarize

router = APIRouter(
    prefix="/assessment",
    tags=["assessment"],
    dependencies=[Depends(require_service("assessment"))],
)

ASSESSMENT_READ = require_permission(
    "assessment.quizzes.read",
    "assessment.results.read",
    "assessment.submissions.submit",
)
ASSESSMENT_RESULTS = require_permission(
    "assessment.results.read",
    "assessment.submissions.grade",
)
ASSESSMENT_MANAGE = require_permission(
    "assessment.quizzes.write",
    "assessment.assignments.create",
)

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


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _quiz_scope_ok(quiz: Quiz, tenant_id: uuid.UUID) -> bool:
    return quiz.school_id is None or quiz.school_id == tenant_id


def _ensure_quiz_scope(quiz: Quiz, tenant_id: uuid.UUID) -> None:
    if not _quiz_scope_ok(quiz, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access is forbidden",
        )


def _ensure_assignment_owner(assignment: Assignment, user: User) -> None:
    if user.role in {"superadmin", "admin", "methodologist"}:
        return
    if assignment.assigned_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assignment belongs to another teacher",
        )


async def _load_quiz(session: AsyncSession, quiz_id: uuid.UUID) -> Quiz | None:
    stmt = (
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions).selectinload(Question.options))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _load_assignment(
    session: AsyncSession, assignment_id: uuid.UUID
) -> Assignment | None:
    stmt = (
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.quiz)
            .selectinload(Quiz.questions)
            .selectinload(Question.options)
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _quiz_out(quiz: Quiz, question_count: int) -> QuizOut:
    return QuizOut.model_validate(quiz).model_copy(
        update={"question_count": question_count}
    )


def _quiz_detail(quiz: Quiz) -> QuizDetailOut:
    questions = sorted(quiz.questions, key=lambda item: (item.order_index, item.prompt))
    payload = _quiz_out(quiz, len(questions)).model_dump()
    payload["questions"] = [QuestionOut.model_validate(item) for item in questions]
    return QuizDetailOut(**payload)


def _assignment_out(
    assignment: Assignment, quiz: Quiz | None, question_count: int
) -> AssignmentOut:
    return AssignmentOut.model_validate(assignment).model_copy(
        update={
            "quiz_title": quiz.title if quiz else None,
            "subject_id": quiz.subject_id if quiz else None,
            "class_number": quiz.class_number if quiz else None,
            "question_count": question_count,
        }
    )


def _public_questions(quiz: Quiz) -> list[QuestionPublicOut]:
    questions = sorted(quiz.questions, key=lambda item: (item.order_index, item.prompt))
    return [QuestionPublicOut.model_validate(item) for item in questions]


def _submission_result(
    submission: Submission, *, late: bool = False
) -> SubmissionResultOut:
    raw_details = submission.answers if isinstance(submission.answers, list) else []
    details = [
        AnswerDetail(**item) for item in raw_details if isinstance(item, dict)
    ]
    percent, grade = summarize(submission.score or 0, submission.max_score or 0)
    return SubmissionResultOut(
        **SubmissionOut.model_validate(submission).model_dump(),
        percent=percent,
        grade=grade,
        late=late,
        details=details,
    )


def _is_started(assignment: Assignment) -> bool:
    return assignment.starts_at is None or assignment.starts_at <= _now()


def _is_late(assignment: Assignment, submitted_at: datetime | None = None) -> bool:
    if assignment.due_at is None:
        return False
    return (submitted_at or _now()) > assignment.due_at


async def _student_class_ids(
    session: AsyncSession, student_id: uuid.UUID
) -> set[uuid.UUID]:
    stmt = select(ClassMembership.class_id).where(
        ClassMembership.user_id == student_id,
        ClassMembership.left_at.is_(None),
    )
    return set((await session.execute(stmt)).scalars().all())


async def _latest_submission(
    session: AsyncSession, assignment_id: uuid.UUID, student_id: uuid.UUID
) -> Submission | None:
    stmt = (
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id,
        )
        .order_by(Submission.attempt_no.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _attempt_count(
    session: AsyncSession, assignment_id: uuid.UUID, student_id: uuid.UUID
) -> int:
    stmt = select(func.count()).select_from(Submission).where(
        Submission.assignment_id == assignment_id,
        Submission.student_id == student_id,
    )
    return int((await session.execute(stmt)).scalar_one())


async def _child_ids(session: AsyncSession, parent_id: uuid.UUID) -> set[uuid.UUID]:
    stmt = select(UserRelation.child_id).where(UserRelation.parent_id == parent_id)
    return set((await session.execute(stmt)).scalars().all())


def _target_matches(
    assignment: Assignment, student_id: uuid.UUID, class_ids: set[uuid.UUID]
) -> bool:
    if assignment.target_type == "student":
        return assignment.student_id == student_id
    if assignment.target_type == "class":
        return assignment.class_id in class_ids
    return False


# ----------------------------------------------------------------- quizzes
@router.post(
    "/quizzes",
    response_model=QuizDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать тест",
    dependencies=[Depends(require_permission("assessment.quizzes.write"))],
)
async def create_quiz(
    payload: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, payload.school_id)
    if payload.subject_id is not None:
        subject = await session.get(Subject, payload.subject_id)
        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")
    for item in payload.questions:
        if item.question_type in {"single_choice", "multiple_choice"}:
            if not item.options:
                raise HTTPException(
                    status_code=400,
                    detail="Choice questions require at least one option",
                )
            if item.correct_answer is None and not any(
                option.is_correct for option in item.options
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Choice questions require a correct option",
                )

    quiz = Quiz(
        title=payload.title,
        quiz_type=payload.quiz_type,
        subject_id=payload.subject_id,
        class_number=payload.class_number,
        school_id=tenant_id,
        created_by=current_user.id,
        time_limit_seconds=payload.time_limit_seconds,
        max_attempts=payload.max_attempts,
        status=payload.status,
        ai_generated=False,
    )
    session.add(quiz)
    await session.flush()
    quiz_id = quiz.id

    for index, item in enumerate(payload.questions):
        question_payload = dict(item.payload)
        if item.correct_answer is not None:
            question_payload["answer"] = item.correct_answer
        question = Question(
            quiz_id=quiz.id,
            question_type=item.question_type,
            prompt=item.prompt,
            payload=question_payload,
            points=item.points,
            order_index=item.order_index or index,
            ai_generated=False,
        )
        session.add(question)
        await session.flush()
        for option_index, option in enumerate(item.options):
            session.add(
                AnswerOption(
                    question_id=question.id,
                    option_text=option.option_text,
                    is_correct=option.is_correct,
                    order_index=option_index,
                )
            )
    await session.commit()
    created = await _load_quiz(session, quiz_id)
    if created is None:
        raise HTTPException(status_code=500, detail="Quiz was not saved")
    return _quiz_detail(created)


@router.get(
    "/quizzes",
    response_model=list[QuizOut],
    summary="Список тестов",
    dependencies=[Depends(require_permission("assessment.quizzes.read"))],
)
async def list_quizzes(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    class_number: int | None = Query(default=None, ge=1, le=11),
    quiz_status: str | None = Query(default=None, alias="status"),
    mine: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    conditions = [or_(Quiz.school_id == tenant_id, Quiz.school_id.is_(None))]
    if subject_id is not None:
        conditions.append(Quiz.subject_id == subject_id)
    if class_number is not None:
        conditions.append(Quiz.class_number == class_number)
    if quiz_status is not None:
        conditions.append(Quiz.status == quiz_status)
    if mine and current_user.role == "teacher":
        conditions.append(Quiz.created_by == current_user.id)

    counts = (
        select(Question.quiz_id, func.count(Question.id).label("cnt"))
        .group_by(Question.quiz_id)
        .subquery()
    )
    stmt = (
        select(Quiz, func.coalesce(counts.c.cnt, 0))
        .outerjoin(counts, counts.c.quiz_id == Quiz.id)
        .where(*conditions)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [_quiz_out(quiz, int(count)) for quiz, count in rows]


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizDetailOut,
    summary="Карточка теста",
    dependencies=[Depends(require_permission("assessment.quizzes.read"))],
)
async def get_quiz(
    quiz_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    quiz = await _load_quiz(session, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _ensure_quiz_scope(quiz, tenant_id)
    return _quiz_detail(quiz)


@router.patch(
    "/quizzes/{quiz_id}",
    response_model=QuizDetailOut,
    summary="Изменить тест",
    dependencies=[Depends(require_permission("assessment.quizzes.write"))],
)
async def update_quiz(
    quiz_id: uuid.UUID,
    payload: QuizUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    quiz = await _load_quiz(session, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _ensure_quiz_scope(quiz, tenant_id)
    if (
        current_user.role not in {"superadmin", "admin", "methodologist"}
        and quiz.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This quiz belongs to another teacher",
        )

    quiz_id = quiz.id
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(quiz, field, value)
    await session.commit()
    refreshed = await _load_quiz(session, quiz_id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Quiz was not saved")
    return _quiz_detail(refreshed)


# -------------------------------------------------------------- assignments
@router.post(
    "/assignments",
    response_model=AssignmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Назначить работу",
    dependencies=[Depends(require_permission("assessment.assignments.create"))],
)
async def create_assignment(
    payload: AssignmentCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, payload.school_id)
    quiz = await _load_quiz(session, payload.quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _ensure_quiz_scope(quiz, tenant_id)
    if payload.status == "published" and quiz.status != "published":
        raise HTTPException(
            status_code=400, detail="Only a published quiz can be assigned"
        )

    starts_at = _as_utc(payload.starts_at)
    due_at = _as_utc(payload.due_at)
    if starts_at and due_at and due_at < starts_at:
        raise HTTPException(
            status_code=400, detail="due_at must be later than starts_at"
        )

    if payload.target_type == "class":
        if payload.class_id is None or payload.student_id is not None:
            raise HTTPException(
                status_code=400,
                detail="class_id is required and student_id must be empty for class target",
            )
        school_class = await session.get(SchoolClass, payload.class_id)
        if school_class is None:
            raise HTTPException(status_code=404, detail="Class not found")
        if school_class.school_id != tenant_id:
            raise HTTPException(status_code=403, detail="Class belongs to another school")
        target_id = school_class.id
    else:
        if payload.student_id is None:
            raise HTTPException(
                status_code=400, detail="student_id is required for student target"
            )
        student = await session.get(User, payload.student_id)
        if student is None or student.role != "student":
            raise HTTPException(status_code=404, detail="Student not found")
        if student.school_id != tenant_id:
            raise HTTPException(
                status_code=403, detail="Student belongs to another school"
            )
        if payload.class_id is not None:
            school_class = await session.get(SchoolClass, payload.class_id)
            if school_class is None or school_class.school_id != tenant_id:
                raise HTTPException(
                    status_code=403, detail="Class belongs to another school"
                )
            membership = (
                await session.execute(
                    select(ClassMembership).where(
                        ClassMembership.class_id == payload.class_id,
                        ClassMembership.user_id == student.id,
                        ClassMembership.left_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if membership is None:
                raise HTTPException(
                    status_code=400, detail="Student is not a member of the class"
                )
        target_id = student.id

    assignment = Assignment(
        quiz_id=quiz.id,
        assigned_by=current_user.id,
        target_type=payload.target_type,
        target_id=target_id,
        class_id=payload.class_id,
        student_id=payload.student_id,
        starts_at=starts_at or (_now() if payload.status == "published" else None),
        due_at=due_at,
        instructions=payload.instructions,
        status=payload.status,
        created_at=_now(),
    )
    session.add(assignment)
    await session.flush()
    response = _assignment_out(assignment, quiz, len(quiz.questions))
    await session.commit()
    return response


@router.get(
    "/assignments",
    response_model=list[AssignmentListItem],
    summary="Список работ",
    dependencies=[Depends(ASSESSMENT_READ)],
)
async def list_assignments(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    assignment_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    tenant_id = ensure_school_access(current_user, school_id)
    counts = (
        select(Question.quiz_id, func.count(Question.id).label("cnt"))
        .group_by(Question.quiz_id)
        .subquery()
    )
    base = (
        select(Assignment, Quiz, func.coalesce(counts.c.cnt, 0))
        .join(Quiz, Quiz.id == Assignment.quiz_id)
        .outerjoin(counts, counts.c.quiz_id == Quiz.id)
    )

    if current_user.role in TEACHER_ROLES:
        conditions = [or_(Quiz.school_id == tenant_id, Quiz.school_id.is_(None))]
        if current_user.role == "teacher":
            conditions.append(Assignment.assigned_by == current_user.id)
        if assignment_status is not None:
            conditions.append(Assignment.status == assignment_status)
        rows = (
            await session.execute(
                base.where(*conditions)
                .order_by(Assignment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [
            AssignmentListItem(
                **_assignment_out(assignment, quiz, int(count)).model_dump()
            )
            for assignment, quiz, count in rows
        ]

    if current_user.role == "student":
        class_ids = await _student_class_ids(session, current_user.id)
        conditions = [
            Assignment.status == "published",
            or_(Assignment.starts_at.is_(None), Assignment.starts_at <= _now()),
            or_(Quiz.school_id == tenant_id, Quiz.school_id.is_(None)),
            or_(
                and_(
                    Assignment.target_type == "student",
                    Assignment.student_id == current_user.id,
                ),
                and_(
                    Assignment.target_type == "class",
                    Assignment.class_id.in_(class_ids),
                ),
            ),
        ]
        rows = (
            await session.execute(
                base.where(*conditions)
                .order_by(Assignment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        assignment_ids = [assignment.id for assignment, _, _ in rows]
        submissions = (
            (
                await session.execute(
                    select(Submission)
                    .where(
                        Submission.assignment_id.in_(assignment_ids),
                        Submission.student_id == current_user.id,
                    )
                    .order_by(Submission.attempt_no.desc())
                )
            )
            .scalars()
            .all()
            if assignment_ids
            else []
        )
        latest: dict[uuid.UUID, Submission] = {}
        for submission in submissions:
            latest.setdefault(submission.assignment_id, submission)
        result: list[AssignmentListItem] = []
        for assignment, quiz, count in rows:
            submission = latest.get(assignment.id)
            result.append(
                AssignmentListItem(
                    **_assignment_out(
                        assignment, quiz, int(count)
                    ).model_dump(),
                    submitted=submission is not None,
                    overdue=_is_late(assignment) and submission is None,
                    result=(
                        _submission_result(
                            submission, late=_is_late(assignment, submission.submitted_at)
                        )
                        if submission
                        else None
                    ),
                )
            )
        return result

    if current_user.role == "parent":
        children = await _child_ids(session, current_user.id)
        if not children:
            return []
        child_class_ids: set[uuid.UUID] = set()
        for child_id in children:
            child_class_ids |= await _student_class_ids(session, child_id)
        conditions = [
            Assignment.status == "published",
            or_(Assignment.starts_at.is_(None), Assignment.starts_at <= _now()),
            or_(Quiz.school_id == tenant_id, Quiz.school_id.is_(None)),
            or_(
                and_(
                    Assignment.target_type == "student",
                    Assignment.student_id.in_(children),
                ),
                and_(
                    Assignment.target_type == "class",
                    Assignment.class_id.in_(child_class_ids),
                ),
            ),
        ]
        rows = (
            await session.execute(
                base.where(*conditions)
                .order_by(Assignment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        assignment_ids = [assignment.id for assignment, _, _ in rows]
        submissions = (
            (
                await session.execute(
                    select(Submission)
                    .where(
                        Submission.assignment_id.in_(assignment_ids),
                        Submission.student_id.in_(children),
                    )
                    .order_by(Submission.attempt_no.desc())
                )
            )
            .scalars()
            .all()
            if assignment_ids
            else []
        )
        student_rows = (
            (
                await session.execute(select(User).where(User.id.in_(children)))
            )
            .scalars()
            .all()
        )
        students = {student.id: student for student in student_rows}
        latest_by_assignment: dict[uuid.UUID, dict[uuid.UUID, Submission]] = {}
        for submission in submissions:
            per_student = latest_by_assignment.setdefault(submission.assignment_id, {})
            per_student.setdefault(submission.student_id, submission)

        result = []
        for assignment, quiz, count in rows:
            per_student = latest_by_assignment.get(assignment.id, {})
            results = []
            for student_id, submission in per_student.items():
                student = students.get(student_id)
                percent, grade = summarize(
                    submission.score or 0, submission.max_score or 0
                )
                raw_details = (
                    submission.answers if isinstance(submission.answers, list) else []
                )
                results.append(
                    StudentResultOut(
                        student_id=student_id,
                        student_name=student.full_name if student else "",
                        submission=SubmissionOut.model_validate(submission),
                        percent=percent,
                        grade=grade,
                        details=[
                            AnswerDetail(**item)
                            for item in raw_details
                            if isinstance(item, dict)
                        ],
                    )
                )
            result.append(
                AssignmentListItem(
                    **_assignment_out(
                        assignment, quiz, int(count)
                    ).model_dump(),
                    results=results,
                )
            )
        return result

    _ensure_role(current_user, STAFF_ROLES)
    return []


@router.get(
    "/assignments/{assignment_id}",
    response_model=AssignmentDetailOut,
    summary="Карточка работы",
    dependencies=[Depends(ASSESSMENT_READ)],
)
async def get_assignment(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(
        default=None, description="Required for a parent request"
    ),
):
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    tenant_id = ensure_school_access(current_user, school_id)
    _ensure_quiz_scope(assignment.quiz, tenant_id)

    base = _assignment_out(
        assignment, assignment.quiz, len(assignment.quiz.questions)
    )

    if current_user.role in TEACHER_ROLES:
        _ensure_assignment_owner(assignment, current_user)
        return AssignmentDetailOut(
            **base.model_dump(),
            questions=_public_questions(assignment.quiz),
        )

    if current_user.role == "student":
        if assignment.status != "published":
            raise HTTPException(status_code=403, detail="Assignment is not published")
        if not _is_started(assignment):
            raise HTTPException(
                status_code=403, detail="Assignment has not started yet"
            )
        class_ids = await _student_class_ids(session, current_user.id)
        if not _target_matches(assignment, current_user.id, class_ids):
            raise HTTPException(status_code=403, detail="Assignment is not available")
        submission = await _latest_submission(session, assignment.id, current_user.id)
        attempts = await _attempt_count(session, assignment.id, current_user.id)
        attempts_left = max(0, assignment.quiz.max_attempts - attempts)
        return AssignmentDetailOut(
            **base.model_dump(),
            questions=_public_questions(assignment.quiz),
            submitted=submission is not None,
            result=(
                _submission_result(
                    submission,
                    late=_is_late(assignment, submission.submitted_at),
                )
                if submission
                else None
            ),
            attempts_used=attempts,
            attempts_left=attempts_left,
        )

    if current_user.role == "parent":
        if assignment.status != "published":
            raise HTTPException(status_code=403, detail="Assignment is not published")
        if not _is_started(assignment):
            raise HTTPException(
                status_code=403, detail="Assignment has not started yet"
            )
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
        if not _target_matches(assignment, student_id, class_ids):
            raise HTTPException(status_code=403, detail="Assignment is not available")
        submission = await _latest_submission(session, assignment.id, student_id)
        attempts = await _attempt_count(session, assignment.id, student_id)
        return AssignmentDetailOut(
            **base.model_dump(),
            questions=_public_questions(assignment.quiz),
            submitted=submission is not None,
            result=(
                _submission_result(
                    submission,
                    late=_is_late(assignment, submission.submitted_at),
                )
                if submission
                else None
            ),
            attempts_used=attempts,
            attempts_left=max(0, assignment.quiz.max_attempts - attempts),
        )

    _ensure_role(current_user, STAFF_ROLES)
    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.post(
    "/assignments/{assignment_id}/publish",
    response_model=AssignmentOut,
    summary="Опубликовать работу",
    dependencies=[Depends(ASSESSMENT_MANAGE)],
)
async def publish_assignment(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    _ensure_assignment_owner(assignment, current_user)
    assignment.status = "published"
    if assignment.starts_at is None:
        assignment.starts_at = _now()
    response = _assignment_out(
        assignment, assignment.quiz, len(assignment.quiz.questions)
    )
    await session.commit()
    return response


@router.post(
    "/assignments/{assignment_id}/close",
    response_model=AssignmentOut,
    summary="Закрыть работу",
    dependencies=[Depends(ASSESSMENT_MANAGE)],
)
async def close_assignment(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    _ensure_assignment_owner(assignment, current_user)
    assignment.status = "closed"
    response = _assignment_out(
        assignment, assignment.quiz, len(assignment.quiz.questions)
    )
    await session.commit()
    return response


@router.delete(
    "/assignments/{assignment_id}",
    response_model=AssignmentOut,
    summary="Архивировать работу",
    dependencies=[Depends(ASSESSMENT_MANAGE)],
)
async def archive_assignment(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    _ensure_assignment_owner(assignment, current_user)
    assignment.status = "archived"
    response = _assignment_out(
        assignment, assignment.quiz, len(assignment.quiz.questions)
    )
    await session.commit()
    return response


# --------------------------------------------------------------- submissions
@router.post(
    "/assignments/{assignment_id}/submit",
    response_model=SubmissionResultOut,
    summary="Сдать работу",
    dependencies=[Depends(require_permission("assessment.submissions.submit"))],
)
async def submit_assignment(
    assignment_id: uuid.UUID,
    payload: SubmissionCreate,
    current_user: CurrentUser,
    session: SessionDep,
):
    _ensure_role(current_user, {"student"})
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    tenant_id = ensure_school_access(current_user, None)
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    if assignment.status != "published":
        raise HTTPException(status_code=403, detail="Assignment is not published")
    if assignment.quiz.status != "published":
        raise HTTPException(status_code=403, detail="Quiz is not published")
    if not _is_started(assignment):
        raise HTTPException(status_code=403, detail="Assignment has not started yet")
    if not assignment.quiz.questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment has no questions",
        )

    class_ids = await _student_class_ids(session, current_user.id)
    if not _target_matches(assignment, current_user.id, class_ids):
        raise HTTPException(status_code=403, detail="Assignment is not available")

    if payload.operation_id is not None:
        existing = (
            await session.execute(
                select(Submission).where(
                    Submission.operation_id == payload.operation_id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            if (
                existing.student_id != current_user.id
                or existing.assignment_id != assignment_id
            ):
                raise HTTPException(
                    status_code=409, detail="Operation ID is already used"
                )
            return _submission_result(
                existing, late=_is_late(assignment, existing.submitted_at)
            )

    attempts = await _attempt_count(session, assignment.id, current_user.id)
    if attempts >= assignment.quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No attempts left for this assignment",
        )

    questions = sorted(
        assignment.quiz.questions, key=lambda item: (item.order_index, item.prompt)
    )
    answers_by_question: dict[uuid.UUID, StudentAnswerIn] = {
        item.question_id: item for item in payload.answers
    }
    details: list[dict] = []
    score = 0
    max_score = 0
    for question in questions:
        max_score += question.points
        given = answers_by_question.get(question.id)
        detail = answer_detail(question, given.answer if given else None)
        details.append(detail)
        if detail["correct"]:
            score += question.points

    now = _now()
    duration = payload.duration_seconds or 0
    submission = Submission(
        assignment_id=assignment.id,
        student_id=current_user.id,
        attempt_no=attempts + 1,
        status="graded",
        started_at=now - timedelta(seconds=duration),
        submitted_at=now,
        score=score,
        max_score=max_score,
        duration_seconds=duration,
        answers=details,
        ai_checked=False,
        teacher_checked=False,
        device_id=payload.device_id,
        operation_id=payload.operation_id,
        created_at=now,
        updated_at=now,
    )
    session.add(submission)
    await session.flush()

    for detail in details:
        session.add(
            Answer(
                submission_id=submission.id,
                question_id=uuid.UUID(str(detail["question_id"])),
                answer_payload={
                    "given": detail["given"],
                    "expected": detail["expected"],
                    "correct": detail["correct"],
                },
                teacher_score=(
                    float(detail["points"]) if detail["correct"] else 0.0
                ),
                is_correct=bool(detail["correct"]),
                answered_at=now,
            )
        )
    response = _submission_result(submission, late=_is_late(assignment, now))
    await session.commit()
    return response


@router.get(
    "/assignments/{assignment_id}/result",
    response_model=SubmissionResultOut,
    summary="Результат ученика",
    dependencies=[Depends(require_permission("assessment.results.read"))],
)
async def get_own_result(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    _ensure_role(current_user, {"student"})
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    tenant_id = ensure_school_access(current_user, None)
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    submission = await _latest_submission(session, assignment_id, current_user.id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Assignment is not submitted yet")
    return _submission_result(
        submission, late=_is_late(assignment, submission.submitted_at)
    )


@router.post(
    "/assignments/{assignment_id}/retry",
    summary="Начать новую попытку",
    dependencies=[Depends(require_permission("assessment.submissions.submit"))],
)
async def retry_assignment(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    _ensure_role(current_user, {"student"})
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    tenant_id = ensure_school_access(current_user, None)
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    attempts = await _attempt_count(session, assignment.id, current_user.id)
    if attempts >= assignment.quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No attempts left for this assignment",
        )
    return {
        "status": "ok",
        "next_attempt_no": attempts + 1,
        "attempts_left": assignment.quiz.max_attempts - attempts,
    }


@router.get(
    "/assignments/{assignment_id}/results",
    response_model=AssignmentResultsOut,
    summary="Результаты работы для учителя",
    dependencies=[Depends(ASSESSMENT_RESULTS)],
)
async def assignment_results(
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
):
    _ensure_role(current_user, TEACHER_ROLES)
    tenant_id = ensure_school_access(current_user, school_id)
    assignment = await _load_assignment(session, assignment_id)
    if assignment is None or assignment.quiz is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_quiz_scope(assignment.quiz, tenant_id)
    _ensure_assignment_owner(assignment, current_user)

    rows = (
        await session.execute(
            select(Submission, User)
            .join(User, User.id == Submission.student_id)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.attempt_no.desc())
        )
    ).all()
    latest: dict[uuid.UUID, tuple[Submission, User]] = {}
    for submission, student in rows:
        latest.setdefault(student.id, (submission, student))

    results: list[StudentResultOut] = []
    for submission, student in latest.values():
        percent, grade = summarize(submission.score or 0, submission.max_score or 0)
        raw_details = (
            submission.answers if isinstance(submission.answers, list) else []
        )
        results.append(
            StudentResultOut(
                student_id=student.id,
                student_name=student.full_name,
                submission=SubmissionOut.model_validate(submission),
                percent=percent,
                grade=grade,
                details=[
                    AnswerDetail(**item)
                    for item in raw_details
                    if isinstance(item, dict)
                ],
            )
        )
    return AssignmentResultsOut(
        assignment=_assignment_out(
            assignment, assignment.quiz, len(assignment.quiz.questions)
        ),
        results=results,
    )
