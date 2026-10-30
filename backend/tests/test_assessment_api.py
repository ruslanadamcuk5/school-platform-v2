"""Tests for the assessment API: quizzes, assignments and submissions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_session
from app.main import app
from app.models.assessment import Assignment, Question, Quiz


class FakeResult:
    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return self._items

    def scalar_one(self):
        return self._scalar

    def scalar_one_or_none(self):
        return self._scalar


ACCESS_MARKERS = (
    "iam.groups",
    "iam.group_memberships",
    "iam.group_permissions",
    "system.services",
    "system.service_activations",
)


def _is_access_query(stmt) -> bool:
    text = str(stmt)
    return any(marker in text for marker in ACCESS_MARKERS)


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []

    async def execute(self, _stmt):
        if _is_access_query(_stmt):
            return FakeResult()
        return self._results.pop(0)

    async def get(self, _model, _ident):
        if getattr(_model, "__name__", "") in {"School", "City"}:
            return None
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        now = datetime.now(timezone.utc)
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
                obj.updated_at = now

    async def commit(self):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _student(school_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        role="student",
        school_id=school_id,
        is_active=True,
        deleted_at=None,
    )


def _teacher(school_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        role="teacher",
        school_id=school_id,
        is_active=True,
        deleted_at=None,
    )


def _quiz(school_id: uuid.UUID, teacher_id: uuid.UUID) -> Quiz:
    quiz = Quiz(
        id=uuid.uuid4(),
        title="Проверочная работа",
        quiz_type="test",
        subject_id=None,
        class_number=5,
        school_id=school_id,
        created_by=teacher_id,
        time_limit_seconds=0,
        max_attempts=2,
        status="published",
        ai_generated=False,
        created_at=_now(),
        updated_at=_now(),
    )
    quiz.questions = []
    return quiz


def _question(quiz: Quiz, answer: str = "4", points: int = 2) -> Question:
    question = Question(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        question_type="number",
        prompt="2 + 2",
        payload={"answer": answer},
        points=points,
        order_index=0,
        ai_generated=False,
    )
    question.options = []
    quiz.questions.append(question)
    return question


def _assignment(
    quiz: Quiz,
    *,
    class_id: uuid.UUID,
    teacher_id: uuid.UUID,
    status: str = "published",
    max_attempts: int | None = None,
) -> Assignment:
    if max_attempts is not None:
        quiz.max_attempts = max_attempts
    assignment = Assignment(
        id=uuid.uuid4(),
        quiz_id=quiz.id,
        assigned_by=teacher_id,
        target_type="class",
        target_id=class_id,
        class_id=class_id,
        student_id=None,
        starts_at=None,
        due_at=None,
        instructions=None,
        status=status,
        created_at=_now(),
    )
    assignment.quiz = quiz
    return assignment


def _client(session: FakeSession, user: SimpleNamespace) -> AsyncClient:
    async def override_user():
        return user

    async def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_assessment_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/assessment/quizzes" in paths
    assert "/api/v1/assessment/quizzes/{quiz_id}" in paths
    assert "/api/v1/assessment/assignments" in paths
    assert "/api/v1/assessment/assignments/{assignment_id}/submit" in paths
    assert "/api/v1/assessment/assignments/{assignment_id}/results" in paths


async def test_assessment_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/assessment/quizzes")
    assert response.status_code == 401


async def test_superadmin_needs_school_scope() -> None:
    session = FakeSession([])
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role="superadmin",
        school_id=None,
        is_active=True,
        deleted_at=None,
    )
    client = _client(session, user)
    try:
        async with client:
            response = await client.get("/api/v1/assessment/quizzes")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


async def test_teacher_lists_quizzes_with_question_counts() -> None:
    school_id = uuid.uuid4()
    teacher = _teacher(school_id)
    quiz = _quiz(school_id, teacher.id)
    _question(quiz)
    _question(quiz)
    session = FakeSession([FakeResult(items=[(quiz, 2)])])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.get(
                "/api/v1/assessment/quizzes", params={"mine": "true"}
            )
        assert response.status_code == 200
        assert response.json()[0]["question_count"] == 2
    finally:
        app.dependency_overrides.clear()


async def test_unknown_quiz_returns_404() -> None:
    school_id = uuid.uuid4()
    session = FakeSession([FakeResult(scalar=None)])
    client = _client(session, _teacher(school_id))
    try:
        async with client:
            response = await client.get(
                f"/api/v1/assessment/quizzes/{uuid.uuid4()}"
            )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_teacher_assigns_quiz_to_class() -> None:
    school_id = uuid.uuid4()
    teacher = _teacher(school_id)
    quiz = _quiz(school_id, teacher.id)
    _question(quiz)
    school_class = SimpleNamespace(id=uuid.uuid4(), school_id=school_id)
    session = FakeSession([FakeResult(scalar=quiz), school_class])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                "/api/v1/assessment/assignments",
                json={
                    "quiz_id": str(quiz.id),
                    "target_type": "class",
                    "class_id": str(school_class.id),
                },
            )
        assert response.status_code == 201
        payload = response.json()
        assert payload["target_type"] == "class"
        assert payload["status"] == "published"
        assert payload["question_count"] == 1
    finally:
        app.dependency_overrides.clear()


async def test_teacher_cannot_assign_to_another_school_class() -> None:
    school_id = uuid.uuid4()
    teacher = _teacher(school_id)
    quiz = _quiz(school_id, teacher.id)
    _question(quiz)
    school_class = SimpleNamespace(id=uuid.uuid4(), school_id=uuid.uuid4())
    session = FakeSession([FakeResult(scalar=quiz), school_class])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                "/api/v1/assessment/assignments",
                json={
                    "quiz_id": str(quiz.id),
                    "target_type": "class",
                    "class_id": str(school_class.id),
                },
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_student_submission_is_auto_graded() -> None:
    school_id = uuid.uuid4()
    student = _student(school_id)
    teacher = _teacher(school_id)
    class_id = uuid.uuid4()
    quiz = _quiz(school_id, teacher.id)
    question = _question(quiz)
    assignment = _assignment(
        quiz, class_id=class_id, teacher_id=teacher.id, max_attempts=2
    )
    session = FakeSession(
        [
            FakeResult(scalar=assignment),
            FakeResult(items=[class_id]),
            FakeResult(scalar=0),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.post(
                f"/api/v1/assessment/assignments/{assignment.id}/submit",
                json={
                    "answers": [
                        {"question_id": str(question.id), "answer": "4"}
                    ],
                    "duration_seconds": 60,
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["score"] == 2.0
        assert payload["max_score"] == 2.0
        assert payload["percent"] == 100
        assert payload["grade"] == 10
        assert payload["details"][0]["correct"] is True
        assert payload["details"][0]["question_id"] == str(question.id)
    finally:
        app.dependency_overrides.clear()


async def test_retry_is_rejected_when_attempts_are_exhausted() -> None:
    school_id = uuid.uuid4()
    student = _student(school_id)
    teacher = _teacher(school_id)
    class_id = uuid.uuid4()
    quiz = _quiz(school_id, teacher.id)
    _question(quiz)
    assignment = _assignment(
        quiz, class_id=class_id, teacher_id=teacher.id, max_attempts=1
    )
    session = FakeSession(
        [
            FakeResult(scalar=assignment),
            FakeResult(scalar=1),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.post(
                f"/api/v1/assessment/assignments/{assignment.id}/retry"
            )
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()
