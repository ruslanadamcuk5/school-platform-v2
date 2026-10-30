"""Tests for the LMS read API and its tenant rules."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_session
from app.main import app


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

    async def execute(self, _stmt):
        if _is_access_query(_stmt):
            return FakeResult()
        return self._results.pop(0)

    async def get(self, _model, _ident):
        if getattr(_model, "__name__", "") in {"School", "City"}:
            return None
        return self._results.pop(0)


def fake_user(role: str = "student", school_id: uuid.UUID | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        school_id=school_id,
        is_active=True,
        deleted_at=None,
    )


def topic_row() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        class_number=5,
        code="fractions",
        title="Дроби",
        title_i18n={"ru": "Дроби"},
        description="Обыкновенные дроби",
        icon="🔢",
        color="indigo",
        part=1,
        page_start=10,
        page_end=18,
        difficulty_level=1,
        order_index=1,
        source="curriculum",
        kind="practice",
        status="active",
    )


async def _client_with_overrides(results, user=None):
    user = user or fake_user()
    session = FakeSession(results)

    async def override_user():
        return user

    async def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_lms_subjects_are_listed() -> None:
    subject = SimpleNamespace(
        id=uuid.uuid4(),
        code="math",
        name="Математика",
        name_i18n={"ru": "Математика"},
        icon="🔢",
        color="indigo",
        description=None,
        is_active=True,
        order_index=0,
    )
    client = await _client_with_overrides([FakeResult(items=[subject])])
    try:
        async with client:
            response = await client.get("/api/v1/lms/subjects")
        assert response.status_code == 200
        assert response.json()[0]["code"] == "math"
    finally:
        app.dependency_overrides.clear()


async def test_lms_topics_support_filters_and_pagination() -> None:
    client = await _client_with_overrides(
        [FakeResult(scalar=1), FakeResult(items=[topic_row()])]
    )
    try:
        async with client:
            response = await client.get(
                "/api/v1/lms/topics",
                params={"grade": 5, "search": "дроб", "limit": 10},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["limit"] == 10
        assert payload["items"][0]["code"] == "fractions"
    finally:
        app.dependency_overrides.clear()


async def test_lms_topic_detail_includes_methods_lessons_and_books() -> None:
    topic = topic_row()
    method = SimpleNamespace(
        id=uuid.uuid4(),
        code="compare",
        name="Сравнение дробей",
        widget=None,
        explanation="Сравниваем числители",
        steps=[],
        example_key=None,
        order_index=0,
    )
    lesson = SimpleNamespace(
        id=uuid.uuid4(),
        title="Урок: Дроби",
        lesson_type="text",
        status="published",
        order_index=0,
    )
    book = SimpleNamespace(
        id=uuid.uuid4(),
        title="Математика 5",
        author="Иванов",
        pages=200,
        file_id=None,
    )
    link = SimpleNamespace(page_from=10, page_to=18)
    client = await _client_with_overrides(
        [
            topic,
            FakeResult(items=[method]),
            FakeResult(items=[lesson]),
            FakeResult(items=[(link, book)]),
        ]
    )
    try:
        async with client:
            response = await client.get(f"/api/v1/lms/topics/{topic.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == "fractions"
        assert payload["methods"][0]["code"] == "compare"
        assert payload["lessons"][0]["title"] == "Урок: Дроби"
        assert payload["textbooks"][0]["title"] == "Математика 5"
    finally:
        app.dependency_overrides.clear()


async def test_lms_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/lms/subjects")
    assert response.status_code == 401


async def test_courses_require_school_for_superadmin() -> None:
    client = await _client_with_overrides(
        [FakeResult(items=[])], user=fake_user(role="superadmin", school_id=None)
    )
    try:
        async with client:
            response = await client.get("/api/v1/lms/courses")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_lms_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/lms/subjects" in paths
    assert "/api/v1/lms/topics" in paths
    assert "/api/v1/lms/topics/{topic_id}" in paths
    assert "/api/v1/lms/textbooks" in paths
    assert "/api/v1/lms/courses" in paths
