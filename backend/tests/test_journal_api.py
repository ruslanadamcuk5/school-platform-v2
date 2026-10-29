"""Tests for the journal API: schedule, entries, bulk grading and summary."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
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


def _class(school_id: uuid.UUID, name: str = "5А"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        grade=5,
        letter="А",
        display_name=name,
        academic_year="2025/2026",
        deleted_at=None,
    )


def _subject(name: str = "Математика"):
    return SimpleNamespace(id=uuid.uuid4(), name=name, icon="📘", code="math")


def _student(school_id: uuid.UUID, name: str = "Иванов Иван"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        role="student",
        school_id=school_id,
        full_name=name,
        login="student@test",
        deleted_at=None,
    )


def _client(session: FakeSession, user: SimpleNamespace) -> AsyncClient:
    async def override_user():
        return user

    async def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_journal_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/journal/schedule" in paths
    assert "/api/v1/journal/schedule/{item_id}" in paths
    assert "/api/v1/journal/entries" in paths
    assert "/api/v1/journal/entries/bulk" in paths
    assert "/api/v1/journal/summary" in paths
    assert "/api/v1/journal/classes/{class_id}/students" in paths


async def test_journal_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/journal/schedule")
    assert response.status_code == 401


async def test_student_schedule_uses_class_membership() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id, "Петров Пётр")
    school_class = _class(school_id)
    subject = _subject()
    teacher = _user("teacher", school_id, "Сидорова Анна")
    schedule_item = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        class_id=school_class.id,
        school_class=school_class,
        subject_id=subject.id,
        subject=subject,
        teacher_id=teacher.id,
        teacher=teacher,
        day_of_week=1,
        lesson_no=1,
        start_time=time(9, 0),
        end_time=time(9, 45),
        room="12",
        topic_id=None,
        topic=None,
        note=None,
        valid_from=date(2025, 9, 1),
        valid_to=None,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession(
        [
            FakeResult(items=[school_class.id]),
            FakeResult(items=[schedule_item]),
        ]
    )
    client = _client(session, student)
    try:
        async with client:
            response = await client.get("/api/v1/journal/schedule")
        assert response.status_code == 200
        payload = response.json()
        assert payload["weekdays"][0] == "Понедельник"
        assert payload["schedule"][0]["subject_name"] == "Математика"
        assert payload["schedule"][0]["class_name"] == "5А"
    finally:
        app.dependency_overrides.clear()


async def test_student_cannot_read_another_student_entries() -> None:
    school_id = uuid.uuid4()
    student = _user("student", school_id)
    session = FakeSession([])
    client = _client(session, student)
    try:
        async with client:
            response = await client.get(
                "/api/v1/journal/entries", params={"student_id": str(uuid.uuid4())}
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_parent_must_pass_child_id() -> None:
    school_id = uuid.uuid4()
    parent = _user("parent", school_id)
    session = FakeSession([])
    client = _client(session, parent)
    try:
        async with client:
            response = await client.get("/api/v1/journal/entries")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


async def test_admin_saves_grade_and_attendance() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id, "Администратор")
    school_class = _class(school_id)
    subject = _subject()
    student = _student(school_id)
    membership = SimpleNamespace(id=uuid.uuid4())
    session = FakeSession(
        [
            school_class,
            subject,
            student,
            FakeResult(scalar=membership),
            FakeResult(scalar=None),
        ]
    )
    client = _client(session, admin)
    try:
        async with client:
            response = await client.post(
                "/api/v1/journal/entries",
                json={
                    "class_id": str(school_class.id),
                    "subject_id": str(subject.id),
                    "student_id": str(student.id),
                    "lesson_date": "2026-10-29",
                    "lesson_topic": "Дроби",
                    "grade": 9,
                    "attendance": "present",
                    "comment": "Активно работал",
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["grade"] == 9
        assert payload["attendance"] == "present"
        assert payload["class_name"] == "5А"
        assert payload["subject_name"] == "Математика"
        assert payload["student_name"] == "Иванов Иван"
        assert len(session.added) == 1
    finally:
        app.dependency_overrides.clear()


async def test_bulk_grading_creates_entries() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id, "Администратор")
    school_class = _class(school_id)
    subject = _subject()
    first = _student(school_id, "Иванов Иван")
    second = _student(school_id, "Петров Пётр")
    session = FakeSession(
        [
            school_class,
            subject,
            FakeResult(items=[first, second]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, admin)
    try:
        async with client:
            response = await client.post(
                "/api/v1/journal/entries/bulk",
                json={
                    "class_id": str(school_class.id),
                    "subject_id": str(subject.id),
                    "lesson_date": "2026-10-29",
                    "lesson_topic": "Дроби",
                    "items": [
                        {
                            "student_id": str(first.id),
                            "grade": 8,
                            "attendance": "present",
                        },
                        {
                            "student_id": str(second.id),
                            "grade": None,
                            "attendance": "absent",
                        },
                    ],
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] == 2
        assert payload["updated"] == 0
        assert len(payload["entries"]) == 2
        assert payload["entries"][1]["attendance"] == "absent"
        assert len(session.added) == 2
    finally:
        app.dependency_overrides.clear()


async def test_journal_summary_groups_grades_and_attendance() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id)
    school_class = _class(school_id)
    student_id = uuid.uuid4()
    student = SimpleNamespace(full_name="Иванов Иван")
    first = SimpleNamespace(
        student_id=student_id,
        grade=8,
        attendance="present",
        student=student,
    )
    second = SimpleNamespace(
        student_id=student_id,
        grade=9,
        attendance="absent",
        student=student,
    )
    session = FakeSession(
        [
            school_class,
            FakeResult(items=[first, second]),
        ]
    )
    client = _client(session, admin)
    try:
        async with client:
            response = await client.get(
                "/api/v1/journal/summary",
                params={"class_id": str(school_class.id)},
            )
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["student_id"] == str(student_id)
        assert item["entries_count"] == 2
        assert item["grades_count"] == 2
        assert item["average_grade"] == 8.5
        assert item["attendance"]["present"] == 1
        assert item["attendance"]["absent"] == 1
    finally:
        app.dependency_overrides.clear()


async def test_schedule_rejects_end_before_start() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id)
    session = FakeSession([])
    client = _client(session, admin)
    try:
        async with client:
            response = await client.post(
                "/api/v1/journal/schedule",
                json={
                    "class_id": str(uuid.uuid4()),
                    "subject_id": str(uuid.uuid4()),
                    "day_of_week": 1,
                    "lesson_no": 1,
                    "start_time": "10:00:00",
                    "end_time": "09:00:00",
                },
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


async def test_existing_entry_is_updated_not_duplicated() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id, "Администратор")
    school_class = _class(school_id)
    subject = _subject()
    student = _student(school_id)
    membership = SimpleNamespace(id=uuid.uuid4())
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        class_id=school_class.id,
        school_class=school_class,
        subject_id=subject.id,
        subject=subject,
        teacher_id=admin.id,
        teacher=admin,
        student_id=student.id,
        student=student,
        lesson_date=date(2026, 10, 29),
        lesson_topic="Старая тема",
        grade=7,
        attendance="present",
        comment=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = FakeSession(
        [
            school_class,
            subject,
            student,
            FakeResult(scalar=membership),
            FakeResult(scalar=existing),
        ]
    )
    client = _client(session, admin)
    try:
        async with client:
            response = await client.post(
                "/api/v1/journal/entries",
                json={
                    "class_id": str(school_class.id),
                    "subject_id": str(subject.id),
                    "student_id": str(student.id),
                    "lesson_date": "2026-10-29",
                    "grade": 9,
                    "attendance": "late",
                },
            )
        assert response.status_code == 200
        assert response.json()["grade"] == 9
        assert response.json()["attendance"] == "late"
        assert session.added == []
    finally:
        app.dependency_overrides.clear()


async def test_date_range_is_validated() -> None:
    school_id = uuid.uuid4()
    admin = _user("admin", school_id)
    session = FakeSession([])
    client = _client(session, admin)
    try:
        async with client:
            response = await client.get(
                "/api/v1/journal/entries",
                params={
                    "date_from": "2026-10-30",
                    "date_to": "2026-10-29",
                },
            )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


async def test_teacher_cannot_edit_foreign_class_schedule() -> None:
    school_id = uuid.uuid4()
    teacher = _user("teacher", school_id, "Сидорова Анна")
    school_class = _class(school_id)
    session = FakeSession(
        [
            school_class,
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[]),
        ]
    )
    client = _client(session, teacher)
    try:
        async with client:
            response = await client.get(
                "/api/v1/journal/schedule",
                params={"class_id": str(school_class.id)},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
