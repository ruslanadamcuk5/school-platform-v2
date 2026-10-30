"""Tests for the library API: access, books, recommendations and catalog."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
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


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.deleted = []

    async def execute(self, _stmt):
        return self._results.pop(0)

    async def get(self, _model, _ident):
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

    async def delete(self, obj):
        self.deleted.append(obj)


def _user(role: str, school_id: uuid.UUID, name: str = "Пользователь"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        school_id=school_id,
        full_name=name,
        login=f"{role}@test",
        is_active=True,
        deleted_at=None,
    )


def _subject(name: str = "Математика"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        name_i18n={},
        icon="📘",
        color="indigo",
        code="math",
        description=None,
        is_active=True,
        order_index=0,
    )


def _topic(subject_id: uuid.UUID, title: str = "Дроби"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=subject_id,
        class_number=5,
        code="fractions",
        title=title,
        icon="📖",
        order_index=1,
    )


def _textbook(subject, topic=None):
    textbook = SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=subject.id,
        subject=subject,
        class_number=5,
        title="Математика 5",
        author="Иванов",
        description="Учебник",
        pages=120,
        status="active",
        topic_links=[],
    )
    if topic is not None:
        textbook.topic_links = [
            SimpleNamespace(
                topic_id=topic.id,
                topic=topic,
                page_from=10,
                page_to=20,
            )
        ]
    return textbook


def _class(
    school_id: uuid.UUID,
    name: str = "5А",
    homeroom_teacher_id: uuid.UUID | None = None,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        grade=5,
        letter="А",
        display_name=name,
        academic_year="2025/2026",
        homeroom_teacher_id=homeroom_teacher_id,
        deleted_at=None,
    )


def _link(school_class, book_id: uuid.UUID | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        book_id=book_id,
        class_id=school_class.id,
        school_class=school_class,
    )


def _book(
    owner,
    textbook,
    subject,
    classes,
    title: str = "Математика 5",
):
    book = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner.id if owner else None,
        owner=owner,
        textbook_id=textbook.id if textbook else None,
        textbook=textbook,
        subject_id=subject.id if subject else None,
        subject=subject,
        class_number=5,
        title=title,
        author="Иванов",
        description="Учебник",
        created_at=datetime.now(timezone.utc),
        class_links=[],
    )
    book.class_links = [_link(klass, book.id) for klass in classes]
    return book


def _client(session: FakeSession, user: SimpleNamespace) -> AsyncClient:
    async def override_user():
        return user

    async def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_library_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/library" in paths
    assert "/api/v1/library/books" in paths
    assert "/api/v1/library/books/{book_id}" in paths
    assert "/api/v1/library/books/{book_id}/recommend" in paths
    assert "/api/v1/library/manage" in paths
    assert "/api/v1/library/catalog" in paths
    assert "/api/v1/library/recommendations" in paths
    assert "/api/v1/library/recommendations/{recommendation_id}/done" in paths


async def test_library_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/library")
    assert response.status_code == 401


async def test_student_library_lists_books_of_own_class() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id, "Петров Пётр")
    school_class = _class(school_id)
    subject = _subject()
    topic = _topic(subject.id)
    textbook = _textbook(subject, topic)
    book = _book(student, textbook, subject, [school_class])
    session = FakeSession(
        [
            FakeResult(items=[school_class.id]),
            FakeResult(items=[book]),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.get("/api/v1/library")
        assert response.status_code == 200
        payload = response.json()
        assert payload["stats"]["books"] == 1
        assert payload["books"][0]["title"] == "Математика 5"
        assert payload["books"][0]["topics_count"] == 1
        assert payload["books"][0]["classes_count"] == 1
    finally:
        app.dependency_overrides.clear()


async def test_student_cannot_open_book_of_foreign_class() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id)
    own_class = _class(school_id)
    other_class = _class(school_id, "6Б")
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(student, textbook, subject, [other_class])
    session = FakeSession(
        [
            FakeResult(scalar=book),
            FakeResult(items=[own_class.id]),
            FakeResult(scalar=None),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.get(f"/api/v1/library/books/{book.id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_student_book_detail_includes_topics_and_recommendations() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id, "Петров Пётр")
    teacher = _user("teacher", school_id, "Сидорова Анна")
    school_class = _class(school_id)
    subject = _subject()
    topic = _topic(subject.id)
    textbook = _textbook(subject, topic)
    book = _book(teacher, textbook, subject, [school_class])
    done_at = datetime.now(timezone.utc)
    rec = SimpleNamespace(
        id=uuid.uuid4(),
        book_id=book.id,
        book=book,
        topic_id=topic.id,
        topic=topic,
        teacher_id=teacher.id,
        teacher=teacher,
        target_type="class",
        class_id=school_class.id,
        school_class=school_class,
        student_id=None,
        student=None,
        note="Прочитать",
        created_at=done_at,
    )
    session = FakeSession(
        [
            FakeResult(scalar=book),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[rec]),
            FakeResult(items=[(rec.id, done_at)]),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.get(f"/api/v1/library/books/{book.id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["topics"][0]["title"] == "Дроби"
        assert payload["recommendations"][0]["done"] is True
        assert payload["manageable"] is False
    finally:
        app.dependency_overrides.clear()


async def test_student_marks_recommendation_done() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id)
    teacher = _user("teacher", school_id)
    school_class = _class(school_id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [school_class])
    rec = SimpleNamespace(
        id=uuid.uuid4(),
        book_id=book.id,
        book=book,
        topic_id=None,
        topic=None,
        teacher_id=teacher.id,
        teacher=teacher,
        target_type="class",
        class_id=school_class.id,
        school_class=school_class,
        student_id=None,
        student=None,
        note=None,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession(
        [
            FakeResult(scalar=rec),
            FakeResult(items=[school_class.id]),
            FakeResult(scalar=None),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.post(
                f"/api/v1/library/recommendations/{rec.id}/done"
            )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert len(session.added) == 1
        assert session.added[0].student_id == student.id
    finally:
        app.dependency_overrides.clear()


async def test_teacher_creates_book_for_own_class() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id, "Сидорова Анна")
    school_class = _class(school_id, homeroom_teacher_id=teacher.id)
    subject = _subject()
    topic = _topic(subject.id)
    textbook = _textbook(subject, topic)
    session = FakeSession(
        [
            FakeResult(scalar=textbook),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
            FakeResult(items=[]),
            school_class,
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                "/api/v1/library/books",
                json={
                    "textbook_id": str(textbook.id),
                    "class_ids": [str(school_class.id)],
                },
            )
        assert response.status_code == 201
        payload = response.json()
        assert payload["title"] == "Математика 5"
        assert payload["classes_count"] == 1
        assert payload["topics_count"] == 1
        assert payload["manageable"] is True
        assert len(session.added) == 1
    finally:
        app.dependency_overrides.clear()


async def test_teacher_cannot_create_book_for_foreign_class() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    school_class = _class(school_id)
    subject = _subject()
    textbook = _textbook(subject)
    session = FakeSession(
        [
            FakeResult(scalar=textbook),
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                "/api/v1/library/books",
                json={
                    "textbook_id": str(textbook.id),
                    "class_ids": [str(school_class.id)],
                },
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_teacher_recommends_book_to_class() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id, "Сидорова Анна")
    school_class = _class(school_id, homeroom_teacher_id=teacher.id)
    subject = _subject()
    topic = _topic(subject.id)
    textbook = _textbook(subject, topic)
    book = _book(teacher, textbook, subject, [school_class])
    session = FakeSession(
        [
            FakeResult(scalar=book),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
            FakeResult(items=[]),
            school_class,
            FakeResult(items=[]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                f"/api/v1/library/books/{book.id}/recommend",
                json={
                    "class_ids": [str(school_class.id)],
                    "topic_id": str(topic.id),
                    "note": "Прочитать к уроку",
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] == 1
        assert payload["skipped"] == 0
        assert payload["items"][0]["class_name"] == "5А"
        assert payload["items"][0]["book_title"] == "Математика 5"
        assert len(session.added) == 1
    finally:
        app.dependency_overrides.clear()


async def test_duplicate_recommendation_is_skipped() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    school_class = _class(school_id, homeroom_teacher_id=teacher.id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [school_class])
    existing = SimpleNamespace(
        target_type="class",
        class_id=school_class.id,
        student_id=None,
    )
    session = FakeSession(
        [
            FakeResult(scalar=book),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
            FakeResult(items=[]),
            school_class,
            FakeResult(items=[existing]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.post(
                f"/api/v1/library/books/{book.id}/recommend",
                json={"class_ids": [str(school_class.id)]},
            )
        assert response.status_code == 200
        assert response.json()["created"] == 0
        assert response.json()["skipped"] == 1
        assert session.added == []
    finally:
        app.dependency_overrides.clear()


async def test_teacher_revokes_recommendation() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    school_class = _class(school_id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [school_class])
    rec = SimpleNamespace(
        id=uuid.uuid4(),
        book_id=book.id,
        book=book,
        topic_id=None,
        topic=None,
        teacher_id=teacher.id,
        teacher=teacher,
        target_type="class",
        class_id=school_class.id,
        school_class=school_class,
        student_id=None,
        student=None,
        note=None,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession([FakeResult(scalar=rec)])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.delete(
                f"/api/v1/library/recommendations/{rec.id}"
            )
        assert response.status_code == 200
        assert len(session.deleted) == 1
    finally:
        app.dependency_overrides.clear()


async def test_teacher_catalog_returns_textbooks_with_topics() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    subject = _subject()
    topic = _topic(subject.id)
    textbook = _textbook(subject, topic)
    session = FakeSession(
        [
            FakeResult(items=[textbook]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.get("/api/v1/library/catalog")
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["book_id"] is None
        assert items[0]["topics"][0]["title"] == "Дроби"
    finally:
        app.dependency_overrides.clear()


async def test_parent_library_uses_default_child() -> None:
    school_id = uuid.uuid4()
    parent = _user("parent", school_id, "Иванова Мария")
    child = _user("student", school_id, "Иванов Иван")
    child.full_name = "Иванов Иван"
    school_class = _class(school_id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(None, textbook, subject, [school_class])
    session = FakeSession(
        [
            FakeResult(items=[child]),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[book]),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, parent)
    try:
        async with client:
            response = await client.get("/api/v1/library")
        assert response.status_code == 200
        payload = response.json()
        assert payload["child"]["id"] == str(child.id)
        assert len(payload["children"]) == 1
        assert payload["stats"]["books"] == 1
    finally:
        app.dependency_overrides.clear()


async def test_parent_cannot_select_foreign_child() -> None:
    school_id = uuid.uuid4()
    parent = _user("parent", school_id)
    child = _user("student", school_id)
    session = FakeSession([FakeResult(items=[child])])
    client = _client(session, parent)
    try:
        async with client:
            response = await client.get(
                "/api/v1/library", params={"student_id": str(uuid.uuid4())}
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_manage_library_returns_classes_students_and_subjects() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    school_class = _class(school_id, homeroom_teacher_id=teacher.id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [school_class])
    student = _user("student", school_id, "Иванов Иван")
    membership = SimpleNamespace(id=uuid.uuid4())
    session = FakeSession(
        [
            FakeResult(items=[book]),
            FakeResult(items=[school_class.id]),
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[school_class]),
            FakeResult(items=[(student, membership, school_class)]),
            FakeResult(items=[subject]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.get("/api/v1/library/manage")
        assert response.status_code == 200
        payload = response.json()
        assert payload["stats"]["books"] == 1
        assert payload["classes"][0]["display_name"] == "5А"
        assert payload["students"][0]["full_name"] == "Иванов Иван"
        assert payload["subjects"][0]["name"] == "Математика"
    finally:
        app.dependency_overrides.clear()


async def test_teacher_updates_book_title() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [])
    session = FakeSession([FakeResult(scalar=book)])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.patch(
                f"/api/v1/library/books/{book.id}",
                json={"title": "Новое название"},
            )
        assert response.status_code == 200
        assert response.json()["title"] == "Новое название"
    finally:
        app.dependency_overrides.clear()


async def test_teacher_deletes_book() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id)
    subject = _subject()
    textbook = _textbook(subject)
    book = _book(teacher, textbook, subject, [])
    session = FakeSession([FakeResult(scalar=book)])
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.delete(f"/api/v1/library/books/{book.id}")
        assert response.status_code == 200
        assert len(session.deleted) == 1
    finally:
        app.dependency_overrides.clear()
