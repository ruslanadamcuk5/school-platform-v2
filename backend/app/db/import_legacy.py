"""Import the legacy Flask/SQLite data into the new PostgreSQL schema.

The source database is opened read-only. Deterministic UUIDs are derived from
legacy identifiers, so the import is idempotent and can be re-run safely.

Usage (from ``backend``)::

    python -m app.db.import_legacy --source ..\\..\\edu-math\\data\\math_tutor.db
    python -m app.db.import_legacy --dry-run

The legacy project is never modified. Password hashes remain in the old
PBKDF2 format and are upgraded to bcrypt on the first successful login.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.ai import AIExplanation, AIRequest, AISetting
from app.models.analytics import (
    Attempt,
    DailyAnswer,
    MethodProgress,
    TopicProgress,
)
from app.models.assessment import (
    Answer,
    AnswerOption,
    Assignment,
    PlaySession,
    Question,
    Quiz,
    Submission,
)
from app.models.audit import AuditEvent
from app.models.communication import Notification
from app.models.iam import User, UserRelation
from app.models.journal import LessonSchedule
from app.models.lms import (
    Course,
    CourseClass,
    CourseTopic,
    Lesson,
    LibraryItem,
    LibraryItemClass,
    LibraryRecommendation,
    LibraryRecommendationStatus,
    Method,
    StoredFile,
    Subject,
    Textbook,
    TextbookTopic,
    Topic,
    UserBadge,
)
from app.models.org import City, ClassMembership, Region, School, SchoolClass
from app.models.system import ImportRun, Setting

LEGACY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "school-platform-v2/legacy")
LEGACY_SOURCE = "edu-math"
DEFAULT_SOURCE = Path(r"C:\Users\adamrv\Documents\edu-math\data\math_tutor.db")
DEFAULT_UPLOADS = Path(r"C:\Users\adamrv\Documents\edu-math\data\uploads")
DEFAULT_STATIC_TEXTBOOK = Path(r"C:\Users\adamrv\Documents\edu-math\static\textbook")

RELATION_MAP = {
    "мама": "mother",
    "mother": "mother",
    "папа": "father",
    "father": "father",
    "опекун": "guardian",
    "guardian": "guardian",
}
QUIZ_TYPE_MAP = {
    "проверочная": "control",
    "контрольная": "exam",
    "домашняя": "homework",
    "диктант": "dictation",
    "тест": "test",
}
STATUS_MAP = {
    "опубликована": "published",
    "published": "published",
    "черновик": "draft",
    "draft": "draft",
}
SKIP_SETTING_KEYS = {"parent_pin_hash", "api_key", "smtp_password", "secret_key"}


def legacy_uuid(kind: str, *parts: Any) -> uuid.UUID:
    value = ":".join(str(part) for part in parts)
    return uuid.uuid5(LEGACY_NAMESPACE, f"{kind}:{value}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_date(value: Any) -> date | None:
    parsed = parse_dt(value)
    return parsed.date() if parsed else None


def parse_time(value: Any) -> time | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_json(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, ValueError):
        return default


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def slug_code(prefix: str, value: str) -> str:
    return f"{prefix}-{value}"[:120]


def old_rows(con: sqlite3.Connection, table: str) -> Iterable[sqlite3.Row]:
    try:
        return con.execute(f'SELECT * FROM "{table}"').fetchall()
    except sqlite3.OperationalError:
        return []


def source_counts(con: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    tables = [
        row["name"]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    for table in tables:
        if table.startswith("sqlite_"):
            continue
        try:
            counts[table] = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0
    return counts


class Importer:
    def __init__(
        self,
        session: AsyncSession,
        con: sqlite3.Connection,
        *,
        uploads: Path,
        static_textbook: Path,
        copy_files: bool = False,
    ) -> None:
        self.session = session
        self.con = con
        self.uploads = uploads
        self.static_textbook = static_textbook
        self.copy_files = copy_files
        self.counts: dict[str, int] = {}
        self.warnings: list[str] = []
        self.school_by_id: dict[int, uuid.UUID] = {}
        self.user_by_id: dict[int, uuid.UUID] = {}
        self.user_school_by_id: dict[int, uuid.UUID | None] = {}
        self.class_by_id: dict[int, uuid.UUID] = {}
        self.class_school_by_id: dict[int, uuid.UUID] = {}
        self.subject_by_id: dict[int, uuid.UUID] = {}
        self.topic_by_id: dict[int, uuid.UUID] = {}
        self.topic_by_slug: dict[str, uuid.UUID] = {}
        self.method_by_topic_code: dict[tuple[str, str], uuid.UUID] = {}
        self.textbook_by_id: dict[int, uuid.UUID] = {}
        self.course_by_id: dict[int, uuid.UUID] = {}
        self.quiz_by_id: dict[int, uuid.UUID] = {}
        self.assignment_by_id: dict[int, uuid.UUID] = {}
        self.questions_by_quiz: dict[uuid.UUID, list[uuid.UUID]] = {}
        self.learner_user_by_id: dict[int, uuid.UUID] = {}
        self.book_by_id: dict[int, uuid.UUID] = {}
        self.recommendation_by_id: dict[int, uuid.UUID] = {}
        self.used_logins: set[str] = set()
        self.used_emails: set[str] = set()
        self.used_parent_codes: set[str] = set()
        self.existing_user_by_id: dict[uuid.UUID, User] = {}

    def inc(self, key: str) -> None:
        self.counts[key] = self.counts.get(key, 0) + 1

    async def merge(self, obj: Any, key: str) -> Any:
        result = await self.session.merge(obj)
        self.inc(key)
        return result

    async def load_user_uniqueness(self) -> None:
        rows = (await self.session.execute(select(User))).scalars().all()
        for user in rows:
            self.existing_user_by_id[user.id] = user
            self.used_logins.add(user.login.lower())
            if user.email:
                self.used_emails.add(user.email.lower())
            if user.parent_code:
                self.used_parent_codes.add(user.parent_code)

    def choose_login(self, old_id: int, desired: str | None) -> str:
        base = (desired or f"legacy_user_{old_id}").strip().lower()
        if not base:
            base = f"legacy_user_{old_id}"
        if base not in self.used_logins:
            self.used_logins.add(base)
            return base
        candidate = f"{base}_legacy"
        if candidate not in self.used_logins:
            self.used_logins.add(candidate)
            return candidate
        candidate = f"{base}_legacy_{old_id}"
        suffix = 2
        while candidate in self.used_logins:
            candidate = f"{base}_legacy_{old_id}_{suffix}"
            suffix += 1
        self.used_logins.add(candidate)
        return candidate

    def choose_email(self, desired: str | None) -> str | None:
        email = clean_text(desired)
        if email is None:
            return None
        normalized = email.lower()
        if normalized in self.used_emails:
            return None
        self.used_emails.add(normalized)
        return email

    def choose_parent_code(self, desired: str | None) -> str | None:
        code = clean_text(desired)
        if code is None:
            return None
        if code in self.used_parent_codes:
            return None
        self.used_parent_codes.add(code)
        return code

    async def import_org(self) -> None:
        regions_by_name: dict[str, uuid.UUID] = {}
        for row in old_rows(self.con, "cities"):
            region_name = clean_text(row["region"]) or "Регион не указан"
            region_id = regions_by_name.get(region_name)
            if region_id is None:
                region_id = legacy_uuid("region", region_name)
                await self.merge(
                    Region(
                        id=region_id,
                        code=slug_code("legacy-region", hashlib.sha1(
                            region_name.encode("utf-8")
                        ).hexdigest()[:12]),
                        name=region_name,
                    ),
                    "org.regions",
                )
                regions_by_name[region_name] = region_id
            city_id = legacy_uuid("city", row["id"])
            await self.merge(
                City(
                    id=city_id,
                    region_id=region_id,
                    code=f"legacy-city-{row['id']}",
                    name=row["name"],
                    city_type="city",
                ),
                "org.cities",
            )

        await self.session.flush()
        cities = {
            row["id"]: legacy_uuid("city", row["id"])
            for row in old_rows(self.con, "cities")
        }
        for row in old_rows(self.con, "schools"):
            school_id = legacy_uuid("school", row["id"])
            self.school_by_id[row["id"]] = school_id
            city_id = cities.get(row["city_id"])
            city_name = None
            if row["city_id"]:
                city_row = self.con.execute(
                    "SELECT name FROM cities WHERE id = ?", (row["city_id"],)
                ).fetchone()
                city_name = city_row["name"] if city_row else None
            await self.merge(
                School(
                    id=school_id,
                    code=f"legacy-school-{row['id']}",
                    name=row["name"],
                    short_name=clean_text(row["short_name"]),
                    city_id=city_id,
                    city=city_name,
                    address=clean_text(row["address"]),
                    director=clean_text(row["director"]),
                    is_active=True,
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "org.schools",
            )

    async def import_users(self) -> None:
        await self.load_user_uniqueness()
        for row in old_rows(self.con, "users"):
            user_id = legacy_uuid("user", row["id"])
            old_login = clean_text(row["login"]) or f"legacy_user_{row['id']}"
            existing = self.existing_user_by_id.get(user_id)
            if existing is not None:
                login = existing.login
                email = existing.email
                parent_code = existing.parent_code
            else:
                if row["id"] == 1 and old_login == "admin":
                    old_login = "admin_legacy"
                login = self.choose_login(row["id"], old_login)
                email = self.choose_email(row["email"])
                parent_code = self.choose_parent_code(row["child_code"])
            role = "superadmin" if row["role"] == "admin" else row["role"]
            if role not in {
                "superadmin",
                "admin",
                "methodologist",
                "teacher",
                "student",
                "parent",
                "psychologist",
                "secretary",
            }:
                role = "student"
            school_id = self.school_by_id.get(row["school_id"]) if row["school_id"] else None
            self.user_by_id[row["id"]] = user_id
            self.user_school_by_id[row["id"]] = school_id
            await self.merge(
                User(
                    id=user_id,
                    school_id=school_id,
                    login=login,
                    email=email,
                    password_hash=row["password_hash"] or "!disabled",
                    role=role,
                    first_name=row["first_name"] or "",
                    last_name=row["last_name"] or "",
                    phone=clean_text(row["phone"]),
                    parent_code=parent_code,
                    avatar=row["avatar"] or "🦊",
                    is_active=bool(row["is_active"]),
                    is_verified=True,
                    must_change_password=row["id"] == 1,
                    last_login_at=parse_dt(row["last_login"]),
                    preferences={
                        "legacy": {
                            "source": LEGACY_SOURCE,
                            "table": "users",
                            "id": row["id"],
                        }
                    },
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "iam.users",
            )

    async def import_learners(self) -> None:
        accounts = {
            row["learner_id"]: row["user_id"]
            for row in old_rows(self.con, "learner_accounts")
        }
        for row in old_rows(self.con, "learners"):
            linked_user_id = accounts.get(row["id"])
            if linked_user_id and linked_user_id in self.user_by_id:
                self.learner_user_by_id[row["id"]] = self.user_by_id[linked_user_id]
                continue
            shadow_id = legacy_uuid("shadow_learner", row["id"])
            school_id = self.user_school_by_id.get(linked_user_id) if linked_user_id else None
            if school_id is None and row["class_id"]:
                school_id = self.class_school_by_id.get(row["class_id"])
            if school_id is None:
                school_id = next(iter(self.school_by_id.values()), None)
            existing = self.existing_user_by_id.get(shadow_id)
            login = existing.login if existing else self.choose_login(
                row["id"], f"legacy_learner_{row['id']}"
            )
            await self.merge(
                User(
                    id=shadow_id,
                    school_id=school_id,
                    login=login,
                    email=None,
                    password_hash="!disabled",
                    role="student",
                    first_name=row["name"] or f"Ученик {row['id']}",
                    last_name="",
                    avatar=row["avatar"] or "🦊",
                    is_active=False,
                    is_verified=False,
                    preferences={
                        "legacy": {
                            "source": LEGACY_SOURCE,
                            "table": "learners",
                            "id": row["id"],
                        },
                        "shadow_learner": True,
                    },
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "iam.users.shadow",
            )
            self.learner_user_by_id[row["id"]] = shadow_id

    async def import_classes(self) -> None:
        for row in old_rows(self.con, "school_classes"):
            class_id = legacy_uuid("class", row["id"])
            self.class_by_id[row["id"]] = class_id
            self.class_school_by_id[row["id"]] = self.school_by_id[row["school_id"]]
            await self.merge(
                SchoolClass(
                    id=class_id,
                    school_id=self.school_by_id[row["school_id"]],
                    grade=row["grade"],
                    letter=row["letter"] or "А",
                    title=clean_text(row["title"]),
                    academic_year=row["year"] or "2025/2026",
                    homeroom_teacher_id=self.user_by_id.get(row["teacher_id"]),
                    is_active=True,
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "org.classes",
            )

        await self.session.flush()
        for row in old_rows(self.con, "class_students"):
            class_id = self.class_by_id.get(row["class_id"])
            student_id = self.user_by_id.get(row["student_id"])
            if class_id is None or student_id is None:
                self.warnings.append(
                    f"class_students skipped: class={row['class_id']} student={row['student_id']}"
                )
                continue
            await self.merge(
                ClassMembership(
                    id=legacy_uuid(
                        "class_membership", row["class_id"], row["student_id"]
                    ),
                    class_id=class_id,
                    user_id=student_id,
                    role_in_class="student",
                    joined_at=parse_dt(row["joined_at"]),
                ),
                "org.class_memberships",
            )

        for row in old_rows(self.con, "parent_children"):
            parent_id = self.user_by_id.get(row["parent_id"])
            child_id = self.user_by_id.get(row["child_id"])
            if parent_id is None or child_id is None:
                self.warnings.append(
                    f"parent_children skipped: parent={row['parent_id']} child={row['child_id']}"
                )
                continue
            await self.merge(
                UserRelation(
                    id=legacy_uuid(
                        "user_relation", row["parent_id"], row["child_id"]
                    ),
                    parent_id=parent_id,
                    child_id=child_id,
                    relation_type=RELATION_MAP.get(str(row["relation"]).lower(), "other"),
                    is_primary=True,
                    verified_at=parse_dt(row["created_at"]),
                    created_at=parse_dt(row["created_at"]),
                ),
                "iam.user_relations",
            )

    async def import_lms(self) -> None:
        for row in old_rows(self.con, "subjects"):
            subject_id = legacy_uuid("subject", row["id"])
            self.subject_by_id[row["id"]] = subject_id
            await self.merge(
                Subject(
                    id=subject_id,
                    code=row["slug"] or f"legacy-subject-{row['id']}",
                    name=row["name"],
                    name_i18n={"ru": row["name"]},
                    icon=row["icon"] or "📘",
                    color=row["color"] or "indigo",
                    description=clean_text(row["description"]),
                    is_active=bool(row["is_active"]),
                    order_index=row["order_index"] or 0,
                ),
                "lms.subjects",
            )

        await self.session.flush()
        for row in old_rows(self.con, "topics"):
            topic_id = legacy_uuid("topic", row["id"])
            self.topic_by_id[row["id"]] = topic_id
            self.topic_by_slug[row["slug"]] = topic_id
            content = parse_json(row["content_json"], [])
            await self.merge(
                Topic(
                    id=topic_id,
                    subject_id=self.subject_by_id[row["subject_id"]],
                    class_number=row["grade"],
                    code=row["slug"],
                    title=row["title"],
                    title_i18n={"ru": row["title"]},
                    description=clean_text(row["description"]),
                    icon=row["icon"] or "📘",
                    color=row["color"] or "indigo",
                    part=row["part"],
                    page_start=row["page_start"],
                    page_end=row["page_end"],
                    difficulty_level=row["min_level"] or 1,
                    order_index=row["order_index"] or 0,
                    source=clean_text(row["source"]),
                    kind=clean_text(row["kind"]),
                    status="active",
                    content=content,
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "lms.topics",
            )
            await self.merge(
                Lesson(
                    id=legacy_uuid("lesson", row["slug"]),
                    topic_id=topic_id,
                    title=f"Урок: {row['title']}",
                    lesson_type="text",
                    content={"pages": content} if content else {},
                    status="published",
                    order_index=0,
                    created_at=parse_dt(row["created_at"]),
                ),
                "lms.lessons",
            )

        await self.session.flush()
        for row in old_rows(self.con, "methods"):
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if topic_id is None:
                self.warnings.append(f"method skipped, topic missing: {row['slug']}")
                continue
            method_id = legacy_uuid("method", row["id"])
            self.method_by_topic_code[(row["topic_slug"], row["slug"])] = method_id
            await self.merge(
                Method(
                    id=method_id,
                    topic_id=topic_id,
                    code=row["slug"],
                    name=row["name"],
                    widget=clean_text(row["widget"]),
                    explanation=clean_text(row["explanation"]),
                    steps=parse_json(row["steps_json"], []),
                    example_key=clean_text(row["example_key"]),
                    order_index=row["order_index"] or 0,
                ),
                "lms.methods",
            )

    def _file_for_textbook(self, row: sqlite3.Row) -> StoredFile:
        filename = row["filename"] or row["original_name"] or f"legacy-{row['id']}.pdf"
        source = self.uploads / filename
        if not source.exists():
            source = self.static_textbook / filename
        checksum = sha256_file(source) if source.exists() else None
        size = source.stat().st_size if source.exists() else row["size_bytes"]
        return StoredFile(
            id=legacy_uuid("file", filename),
            owner_id=self.user_by_id.get(row["uploaded_by"]),
            storage_key=f"legacy/textbooks/{filename}",
            original_name=row["original_name"] or filename,
            mime_type="application/pdf",
            size_bytes=size,
            checksum=checksum,
            virus_scan_status="legacy_not_scanned",
            created_at=parse_dt(row["created_at"]),
        )

    async def import_textbooks(self) -> None:
        for row in old_rows(self.con, "textbooks"):
            file_model = self._file_for_textbook(row)
            await self.merge(file_model, "lms.files")
            await self.session.flush()
            textbook_id = legacy_uuid("textbook", row["id"])
            self.textbook_by_id[row["id"]] = textbook_id
            await self.merge(
                Textbook(
                    id=textbook_id,
                    subject_id=self.subject_by_id[row["subject_id"]],
                    class_number=row["grade"],
                    title=row["title"],
                    author=clean_text(row["author"]),
                    publisher=clean_text(row["publisher"]),
                    year=clean_text(row["year"]),
                    description=clean_text(row["description"]),
                    pages=row["pages"],
                    file_id=file_model.id,
                    uploaded_by=self.user_by_id.get(row["uploaded_by"]),
                    status="active",
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "lms.textbooks",
            )

        await self.session.flush()
        for row in old_rows(self.con, "textbook_topics"):
            textbook_id = self.textbook_by_id.get(row["textbook_id"])
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if textbook_id is None or topic_id is None:
                self.warnings.append(
                    f"textbook_topic skipped: textbook={row['textbook_id']} topic={row['topic_slug']}"
                )
                continue
            await self.merge(
                TextbookTopic(
                    id=legacy_uuid(
                        "textbook_topic", row["textbook_id"], row["topic_slug"]
                    ),
                    textbook_id=textbook_id,
                    topic_id=topic_id,
                    page_from=row["page"],
                    page_to=row["page_end"],
                ),
                "lms.textbook_topics",
            )

    async def import_courses(self) -> None:
        for row in old_rows(self.con, "courses"):
            course_id = legacy_uuid("course", row["id"])
            self.course_by_id[row["id"]] = course_id
            teacher_id = self.user_by_id.get(row["teacher_id"])
            school_id = self.school_by_id.get(row["school_id"]) if row["school_id"] else None
            if school_id is None and teacher_id is not None:
                school_id = self.user_school_by_id.get(row["teacher_id"])
            if school_id is None:
                school_id = next(iter(self.school_by_id.values()), None)
            await self.merge(
                Course(
                    id=course_id,
                    subject_id=self.subject_by_id[row["subject_id"]],
                    title=row["title"],
                    description=clean_text(row["description"]),
                    grade=row["grade"],
                    teacher_id=teacher_id,
                    school_id=school_id,
                    is_active=bool(row["is_active"]),
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["created_at"]),
                ),
                "lms.courses",
            )

        await self.session.flush()
        for row in old_rows(self.con, "course_topics"):
            course_id = self.course_by_id.get(row["course_id"])
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if course_id is None or topic_id is None:
                self.warnings.append(
                    f"course_topic skipped: course={row['course_id']} topic={row['topic_slug']}"
                )
                continue
            await self.merge(
                CourseTopic(
                    id=legacy_uuid(
                        "course_topic", row["course_id"], row["topic_slug"]
                    ),
                    course_id=course_id,
                    topic_id=topic_id,
                    order_index=row["order_index"] or 0,
                    enabled=bool(row["enabled"]),
                ),
                "lms.course_topics",
            )

        for row in old_rows(self.con, "course_classes"):
            course_id = self.course_by_id.get(row["course_id"])
            class_id = self.class_by_id.get(row["class_id"])
            if course_id is None or class_id is None:
                self.warnings.append(
                    f"course_class skipped: course={row['course_id']} class={row['class_id']}"
                )
                continue
            await self.merge(
                CourseClass(
                    id=legacy_uuid(
                        "course_class", row["course_id"], row["class_id"]
                    ),
                    course_id=course_id,
                    class_id=class_id,
                ),
                "lms.course_classes",
            )

    async def import_assessment(self) -> None:
        for row in old_rows(self.con, "assignments"):
            class_id = self.class_by_id.get(row["class_id"])
            teacher_id = self.user_by_id.get(row["teacher_id"])
            subject_id = self.subject_by_id.get(row["subject_id"])
            class_row = self.con.execute(
                "SELECT grade, school_id FROM school_classes WHERE id = ?",
                (row["class_id"],),
            ).fetchone() if row["class_id"] else None
            school_id = (
                self.school_by_id.get(class_row["school_id"])
                if class_row and class_row["school_id"]
                else self.user_school_by_id.get(row["teacher_id"])
            )
            quiz_id = legacy_uuid("quiz", row["id"])
            self.quiz_by_id[row["id"]] = quiz_id
            await self.merge(
                Quiz(
                    id=quiz_id,
                    title=row["title"],
                    quiz_type=QUIZ_TYPE_MAP.get(str(row["kind"]).lower(), "test"),
                    subject_id=subject_id,
                    class_number=class_row["grade"] if class_row else None,
                    school_id=school_id,
                    created_by=teacher_id,
                    time_limit_seconds=(row["time_limit"] or 0) * 60,
                    max_attempts=1,
                    status=STATUS_MAP.get(str(row["status"]).lower(), "draft"),
                    ai_generated=False,
                    created_at=parse_dt(row["created_at"]),
                    updated_at=parse_dt(row["published_at"] or row["created_at"]),
                ),
                "assessment.quizzes",
            )
            await self.session.flush()

            questions = parse_json(row["questions_json"], [])
            question_ids: list[uuid.UUID] = []
            for index, question in enumerate(questions):
                if not isinstance(question, dict):
                    question = {"question": str(question)}
                question_id = legacy_uuid("question", row["id"], index)
                question_ids.append(question_id)
                answer_type = str(question.get("answer_type") or "text")
                question_type = {
                    "number": "number",
                    "text": "text",
                    "choice": "single_choice",
                    "multi": "multiple_choice",
                }.get(answer_type, "text")
                prompt = (
                    clean_text(question.get("question"))
                    or clean_text(question.get("prompt"))
                    or f"Вопрос {index + 1}"
                )
                await self.merge(
                    Question(
                        id=question_id,
                        quiz_id=quiz_id,
                        question_type=question_type,
                        prompt=prompt,
                        payload=question,
                        points=1,
                        order_index=index,
                        ai_generated=False,
                    ),
                    "assessment.questions",
                )
                choices = question.get("choices") or []
                expected = question.get("answer")
                for option_index, choice in enumerate(choices):
                    if isinstance(choice, dict):
                        option_text = str(
                            choice.get("text") or choice.get("label") or choice
                        )
                        is_correct = bool(choice.get("correct", False))
                    else:
                        option_text = str(choice)
                        is_correct = str(choice) == str(expected)
                    await self.merge(
                        AnswerOption(
                            id=legacy_uuid(
                                "answer_option", row["id"], index, option_index
                            ),
                            question_id=question_id,
                            option_text=option_text,
                            is_correct=is_correct,
                            order_index=option_index,
                        ),
                        "assessment.answer_options",
                    )
            self.questions_by_quiz[quiz_id] = question_ids

            target_id = class_id
            student_id = self.user_by_id.get(row["student_id"]) if row["student_id"] else None
            if student_id is not None and class_id is None:
                target_id = student_id
            assignment_id = legacy_uuid("assignment", row["id"])
            self.assignment_by_id[row["id"]] = assignment_id
            await self.merge(
                Assignment(
                    id=assignment_id,
                    quiz_id=quiz_id,
                    assigned_by=teacher_id,
                    target_type="student" if student_id else "class",
                    target_id=target_id,
                    class_id=class_id,
                    student_id=student_id,
                    starts_at=parse_dt(row["published_at"] or row["created_at"]),
                    due_at=parse_dt(row["due_date"]),
                    instructions=clean_text(row["description"]),
                    status=STATUS_MAP.get(str(row["status"]).lower(), "draft"),
                    created_at=parse_dt(row["created_at"]),
                ),
                "assessment.assignments",
            )

        for row in old_rows(self.con, "assignment_results"):
            assignment_id = self.assignment_by_id.get(row["assignment_id"])
            student_id = self.user_by_id.get(row["student_id"])
            if assignment_id is None or student_id is None:
                self.warnings.append(
                    f"assignment_result skipped: assignment={row['assignment_id']} student={row['student_id']}"
                )
                continue
            submission_id = legacy_uuid("submission", row["id"])
            answers = parse_json(row["answers"], [])
            completed_at = parse_dt(row["completed_at"])
            await self.merge(
                Submission(
                    id=submission_id,
                    assignment_id=assignment_id,
                    student_id=student_id,
                    attempt_no=1,
                    status="graded",
                    started_at=parse_dt(row["started_at"]),
                    submitted_at=completed_at,
                    score=row["score"],
                    max_score=row["max_score"],
                    duration_seconds=row["duration_sec"],
                    answers=answers,
                    ai_checked=False,
                    teacher_checked=True,
                    operation_id=legacy_uuid("operation", "assignment_result", row["id"]),
                    created_at=parse_dt(row["started_at"]),
                    updated_at=completed_at,
                ),
                "assessment.submissions",
            )
            quiz_id = self.quiz_by_id.get(row["assignment_id"])
            question_ids = self.questions_by_quiz.get(quiz_id, []) if quiz_id else []
            for index, answer in enumerate(answers if isinstance(answers, list) else []):
                if not isinstance(answer, dict):
                    answer = {"given": str(answer)}
                question_id = question_ids[index] if index < len(question_ids) else None
                is_correct = answer.get("correct")
                await self.merge(
                    Answer(
                        id=legacy_uuid("answer", row["id"], index),
                        submission_id=submission_id,
                        question_id=question_id,
                        answer_payload=answer,
                        teacher_score=1 if is_correct else 0,
                        teacher_feedback=clean_text(answer.get("solution")),
                        is_correct=bool(is_correct) if is_correct is not None else None,
                        answered_at=completed_at,
                    ),
                    "assessment.answers",
                )

    async def import_schedule(self) -> None:
        for row in old_rows(self.con, "schedules"):
            class_id = self.class_by_id.get(row["class_id"])
            subject_id = self.subject_by_id.get(row["subject_id"])
            if class_id is None or subject_id is None:
                self.warnings.append(
                    f"schedule skipped: class={row['class_id']} subject={row['subject_id']}"
                )
                continue
            class_row = self.con.execute(
                "SELECT school_id, year FROM school_classes WHERE id = ?",
                (row["class_id"],),
            ).fetchone()
            school_id = self.school_by_id.get(class_row["school_id"])
            start = parse_time(row["time_start"])
            end = parse_time(row["time_end"])
            if start is None or end is None:
                self.warnings.append(f"schedule skipped, bad time: {row['id']}")
                continue
            year_start = 2025
            if class_row and class_row["year"]:
                try:
                    year_start = int(str(class_row["year"]).split("/")[0])
                except ValueError:
                    pass
            await self.merge(
                LessonSchedule(
                    id=legacy_uuid("schedule", row["id"]),
                    school_id=school_id,
                    class_id=class_id,
                    subject_id=subject_id,
                    teacher_id=self.user_by_id.get(row["teacher_id"]),
                    day_of_week=row["weekday"],
                    lesson_no=row["lesson_no"],
                    start_time=start,
                    end_time=end,
                    topic_id=self.topic_by_slug.get(row["topic_slug"]),
                    note=clean_text(row["note"]),
                    valid_from=date(year_start, 9, 1),
                    valid_to=date(year_start + 1, 5, 31),
                    created_at=datetime.now(timezone.utc),
                ),
                "journal.lesson_schedule",
            )

    async def import_library(self) -> None:
        for row in old_rows(self.con, "library_books"):
            book_id = legacy_uuid("library_item", row["id"])
            self.book_by_id[row["id"]] = book_id
            await self.merge(
                LibraryItem(
                    id=book_id,
                    owner_id=self.user_by_id.get(row["owner_id"]),
                    textbook_id=self.textbook_by_id.get(row["textbook_id"]),
                    subject_id=self.subject_by_id.get(row["subject_id"]),
                    class_number=row["grade"],
                    title=row["title"],
                    author=clean_text(row["author"]),
                    description=clean_text(row["description"]),
                    created_at=parse_dt(row["created_at"]),
                ),
                "lms.library_items",
            )

        for row in old_rows(self.con, "library_book_classes"):
            book_id = self.book_by_id.get(row["book_id"])
            class_id = self.class_by_id.get(row["class_id"])
            if book_id is None or class_id is None:
                self.warnings.append(
                    f"library_book_class skipped: book={row['book_id']} class={row['class_id']}"
                )
                continue
            await self.merge(
                LibraryItemClass(
                    id=legacy_uuid(
                        "library_item_class", row["book_id"], row["class_id"]
                    ),
                    book_id=book_id,
                    class_id=class_id,
                    added_at=parse_dt(row["added_at"]),
                ),
                "lms.library_item_classes",
            )

        for row in old_rows(self.con, "library_recommendations"):
            rec_id = legacy_uuid("library_recommendation", row["id"])
            self.recommendation_by_id[row["id"]] = rec_id
            target_type = row["target_kind"] if row["target_kind"] in {"class", "student"} else "class"
            await self.merge(
                LibraryRecommendation(
                    id=rec_id,
                    teacher_id=self.user_by_id.get(row["teacher_id"]),
                    book_id=self.book_by_id.get(row["book_id"]),
                    topic_id=self.topic_by_slug.get(row["topic_slug"]),
                    target_type=target_type,
                    student_id=self.user_by_id.get(row["student_id"]),
                    class_id=self.class_by_id.get(row["class_id"]),
                    note=clean_text(row["note"]),
                    created_at=parse_dt(row["created_at"]),
                ),
                "lms.library_recommendations",
            )

        for row in old_rows(self.con, "library_recommendation_done"):
            rec_id = self.recommendation_by_id.get(row["rec_id"])
            student_id = self.user_by_id.get(row["student_id"])
            if rec_id is None or student_id is None:
                self.warnings.append(
                    f"recommendation_done skipped: rec={row['rec_id']} student={row['student_id']}"
                )
                continue
            await self.merge(
                LibraryRecommendationStatus(
                    id=legacy_uuid(
                        "library_recommendation_status", row["rec_id"], row["student_id"]
                    ),
                    recommendation_id=rec_id,
                    student_id=student_id,
                    done_at=parse_dt(row["done_at"]),
                ),
                "lms.library_recommendation_status",
            )

    async def import_analytics(self) -> None:
        for row in old_rows(self.con, "attempts"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if user_id is None:
                self.warnings.append(f"attempt skipped, learner missing: {row['id']}")
                continue
            method_id = None
            if row["topic_slug"] and row["method_slug"]:
                method_id = self.method_by_topic_code.get(
                    (row["topic_slug"], row["method_slug"])
                )
            await self.merge(
                Attempt(
                    id=legacy_uuid("attempt", row["id"]),
                    user_id=user_id,
                    topic_id=topic_id,
                    method_id=method_id,
                    generator=clean_text(row["generator"]),
                    correct=bool(row["correct"]),
                    given_answer=clean_text(row["given_answer"]),
                    expected=clean_text(row["expected"]),
                    time_ms=row["time_ms"],
                    hints_used=row["hints_used"] or 0,
                    mode=row["mode"] or "practice",
                    created_at=parse_dt(row["created_at"]),
                ),
                "analytics.attempts",
            )

        for row in old_rows(self.con, "topic_progress"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if user_id is None or topic_id is None:
                self.warnings.append(f"topic_progress skipped: learner={row['learner_id']}")
                continue
            await self.merge(
                TopicProgress(
                    id=legacy_uuid("topic_progress", row["learner_id"], row["topic_slug"]),
                    user_id=user_id,
                    topic_id=topic_id,
                    stars=row["stars"] or 0,
                    best_streak=row["best_streak"] or 0,
                    best_accuracy=row["best_accuracy"] or 0,
                    attempts=row["attempts"] or 0,
                    correct=row["correct"] or 0,
                    boss_cleared=bool(row["boss_cleared"]),
                    updated_at=parse_dt(row["updated_at"]),
                ),
                "analytics.topic_progress",
            )

        for row in old_rows(self.con, "method_progress"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            method_id = self.method_by_topic_code.get(
                (row["topic_slug"], row["method_slug"])
            )
            if user_id is None or method_id is None:
                self.warnings.append(f"method_progress skipped: learner={row['learner_id']}")
                continue
            await self.merge(
                MethodProgress(
                    id=legacy_uuid(
                        "method_progress", row["learner_id"], row["topic_slug"], row["method_slug"]
                    ),
                    user_id=user_id,
                    method_id=method_id,
                    seen=bool(row["seen"]),
                    attempts=row["attempts"] or 0,
                    correct=row["correct"] or 0,
                    mastered=bool(row["mastered"]),
                    updated_at=parse_dt(row["updated_at"]),
                ),
                "analytics.method_progress",
            )

        for row in old_rows(self.con, "daily_answers"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            if user_id is None:
                continue
            await self.merge(
                DailyAnswer(
                    id=legacy_uuid(
                        "daily_answer", row["learner_id"], row["day"], row["generator"]
                    ),
                    user_id=user_id,
                    day=parse_date(row["day"]),
                    generator=row["generator"],
                    correct=row["correct"] or 0,
                ),
                "analytics.daily_answers",
            )

        for row in old_rows(self.con, "badges"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            if user_id is None:
                continue
            await self.merge(
                UserBadge(
                    id=legacy_uuid("user_badge", row["learner_id"], row["badge_key"]),
                    user_id=user_id,
                    badge_key=row["badge_key"],
                    earned_at=parse_dt(row["earned_at"]),
                ),
                "lms.user_badges",
            )

        for row in old_rows(self.con, "play_sessions"):
            user_id = self.learner_user_by_id.get(row["learner_id"])
            if user_id is None:
                continue
            await self.merge(
                PlaySession(
                    id=legacy_uuid("play_session", row["id"]),
                    user_id=user_id,
                    topic_id=self.topic_by_slug.get(row["topic_slug"]),
                    mode=row["mode"] or "practice",
                    started_at=parse_dt(row["started_at"]),
                    ended_at=parse_dt(row["ended_at"]),
                    task_count=row["task_count"] or 0,
                    correct_count=row["correct_count"] or 0,
                    xp_gained=row["xp_gained"] or 0,
                    round_state=parse_json(row["round_state"], {}),
                ),
                "assessment.play_sessions",
            )

    async def import_notifications(self) -> None:
        for row in old_rows(self.con, "app_notifications"):
            user_id = self.user_by_id.get(row["user_id"])
            if user_id is None:
                continue
            created_at = parse_dt(row["created_at"])
            await self.merge(
                Notification(
                    id=legacy_uuid("notification", row["id"]),
                    user_id=user_id,
                    channel="in_app",
                    notification_type=row["kind"] or "system",
                    title=row["title"] or "Уведомление",
                    body=clean_text(row["body"]),
                    payload={
                        "assignment_id": row["assignment_id"],
                        "student_id": row["student_id"],
                    },
                    read_at=created_at if row["is_read"] else None,
                    sent_at=created_at,
                    status="sent",
                    created_at=created_at,
                ),
                "communication.notifications",
            )

    async def import_ai(self) -> None:
        for row in old_rows(self.con, "ai_settings"):
            if row["api_key"]:
                self.warnings.append(
                    "AI API key was not imported; configure it through the secrets store"
                )
            await self.merge(
                AISetting(
                    id=legacy_uuid("ai_setting", row["id"]),
                    provider=row["provider"] or "openrouter",
                    base_url=clean_text(row["base_url"]),
                    model=row["model"] or "deepseek/deepseek-chat",
                    encrypted_api_key=None,
                    system_prompt=clean_text(row["system_note"]),
                    is_enabled=bool(row["enabled"]),
                    max_tokens=row["max_tokens"] or 900,
                    temperature=row["temperature"] or 0.3,
                    updated_at=parse_dt(row["updated_at"]),
                ),
                "ai.settings",
            )

        for row in old_rows(self.con, "ai_explanations"):
            topic_id = self.topic_by_slug.get(row["topic_slug"])
            if topic_id is None:
                continue
            await self.merge(
                AIExplanation(
                    id=legacy_uuid("ai_explanation", row["id"]),
                    topic_id=topic_id,
                    grade=row["grade"],
                    model=row["model"] or "unknown",
                    content=row["content"] or "",
                    created_at=parse_dt(row["created_at"]),
                ),
                "ai.explanations",
            )

        for row in old_rows(self.con, "ai_requests"):
            await self.merge(
                AIRequest(
                    id=legacy_uuid("ai_request", row["id"]),
                    user_id=self.user_by_id.get(row["user_id"]),
                    request_type=row["kind"] or "unknown",
                    model=clean_text(row["model"]),
                    prompt_preview=clean_text(row["detail"]),
                    status="success" if row["ok"] else "error",
                    created_at=parse_dt(row["created_at"]),
                ),
                "ai.requests",
            )

    async def import_audit(self) -> None:
        for row in old_rows(self.con, "audit_log"):
            user_id = self.user_by_id.get(row["user_id"])
            details = parse_json(row["details"], None)
            if not isinstance(details, dict):
                details = {"legacy": row["details"]}
            await self.merge(
                AuditEvent(
                    id=legacy_uuid("audit_event", row["id"]),
                    school_id=self.user_school_by_id.get(row["user_id"]),
                    user_id=user_id,
                    action=row["action"] or "legacy",
                    entity_type=row["entity"] or "legacy",
                    entity_id=str(row["entity_id"]) if row["entity_id"] else None,
                    details=details,
                    created_at=parse_dt(row["created_at"]),
                ),
                "audit.events",
            )

    async def import_settings(self) -> None:
        for row in old_rows(self.con, "app_meta"):
            key = row["key"]
            if key in SKIP_SETTING_KEYS:
                self.warnings.append(f"secret app_meta key not imported: {key}")
                continue
            await self.merge(
                Setting(
                    key=f"legacy.{key}",
                    value=parse_json(row["value"], row["value"]),
                    description="Imported from edu-math app_meta",
                    updated_by="legacy-import",
                ),
                "system.settings",
            )

    async def run(self) -> None:
        steps = (
            self.import_org,
            self.import_users,
            self.import_classes,
            self.import_learners,
            self.import_lms,
            self.import_textbooks,
            self.import_courses,
            self.import_assessment,
            self.import_schedule,
            self.import_library,
            self.import_analytics,
            self.import_notifications,
            self.import_ai,
            self.import_audit,
            self.import_settings,
        )
        for step in steps:
            await step()
            # Flush each stage so foreign keys are visible to the next one.
            await self.session.flush()


async def run_import(
    source: Path,
    *,
    uploads: Path,
    static_textbook: Path,
    dry_run: bool,
) -> int:
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1
    checksum_before = sha256_file(source)
    con = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    counts = source_counts(con)
    print(f"source: {source}")
    print(f"sha256: {checksum_before}")
    print("source rows:")
    for table, count in counts.items():
        print(f"  {table}: {count}")

    if dry_run:
        con.close()
        print("dry run complete; no database changes")
        return 0

    async with AsyncSessionLocal() as session:
        run = ImportRun(
            source_path=str(source),
            source_sha256=checksum_before,
            status="running",
            counts={},
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

        importer = Importer(
            session,
            con,
            uploads=uploads,
            static_textbook=static_textbook,
        )
        try:
            await importer.run()
            run.status = "completed"
            run.finished_at = datetime.now(timezone.utc)
            run.counts = {
                "source": counts,
                "imported": importer.counts,
                "warnings": importer.warnings,
            }
            run.notes = (
                f"Imported from {source}; old DB was opened read-only. "
                "AI API key and secret app_meta keys were skipped."
            )
            await session.commit()
            print("\nimported rows:")
            for key, count in importer.counts.items():
                print(f"  {key}: {count}")
            if importer.warnings:
                print("\nwarnings:")
                for warning in importer.warnings[:50]:
                    print(f"  - {warning}")
                if len(importer.warnings) > 50:
                    print(f"  ... and {len(importer.warnings) - 50} more")
        except Exception as exc:
            await session.rollback()
            run = await session.get(ImportRun, run_id)
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.notes = f"{type(exc).__name__}: {exc}"
                await session.commit()
            raise

    checksum_after = sha256_file(source)
    con.close()
    if checksum_before != checksum_after:
        print("ERROR: source database changed during import", file=sys.stderr)
        return 2
    print(f"source unchanged: {checksum_after}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--uploads", type=Path, default=DEFAULT_UPLOADS)
    parser.add_argument(
        "--static-textbook", type=Path, default=DEFAULT_STATIC_TEXTBOOK
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(
            run_import(
                args.source,
                uploads=args.uploads,
                static_textbook=args.static_textbook,
                dry_run=args.dry_run,
            )
        )
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    raise SystemExit(main())
