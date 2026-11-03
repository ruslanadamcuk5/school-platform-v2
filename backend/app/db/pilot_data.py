"""Idempotent synthetic pilot data for all four education levels.

The script fills the pilot database with realistic, but completely synthetic
school, college and university data.  It is deliberately deterministic so it
can be run repeatedly without creating duplicates or changing existing
passwords.

Run from the backend directory::

    python -m app.db.pilot_data

The generated credentials are written to ``backend/secrets/`` which is ignored
by Git.  Never commit that file.
"""
from __future__ import annotations

import asyncio
import csv
import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR, settings
from app.core.scopes import COUNTRY_SCOPE_ID
from app.core.security import hash_password
from app.db.seed import (
    CATEGORY_NAME,
    ROLE_FOR_CATEGORY,
    _add_membership,
    _get_or_create_group,
    _grant_permissions,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.assessment import (
    Answer,
    AnswerOption,
    Assignment,
    GradingScale,
    Question,
    Quiz,
    Submission,
)
from app.models.education import (
    CurriculumComponent,
    EducationCurriculum,
    EducationProgram,
    StaffAcademicProfile,
    StudentAcademicProfile,
)
from app.models.iam import User, UserGroup, UserRelation
from app.models.journal import JournalEntry, LessonSchedule
from app.models.lms import (
    LibraryItem,
    LibraryItemClass,
    LibraryRecommendation,
    Subject,
    Textbook,
    TextbookTopic,
    Topic,
)
from app.models.org import City, ClassMembership, School, SchoolClass, TeacherSubject
from app.models.system import ServiceActivation
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE

DEMO_TAG = "synthetic_pilot_2026"
ACADEMIC_YEAR = settings.seed_academic_year
ENROLLMENT_YEAR = 2026
JOINED_AT = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
NOW = datetime.now(timezone.utc)
FIRST_DAY = date(2026, 9, 1)
LAST_DAY = date(2027, 5, 31)
SCHOOL_SUBJECTS: tuple[tuple[str, str, str, str, str, int], ...] = (
    ("math", "Математика", "Mathematics", "📐", "indigo", 10),
    ("russian", "Русский язык", "Russian language", "📖", "rose", 20),
    ("belarusian", "Беларуская мова", "Belarusian language", "📗", "emerald", 30),
    ("literature", "Литература", "Literature", "📚", "amber", 40),
    ("english", "Английский язык", "English", "🌍", "sky", 50),
    ("world", "Человек и мир", "People and the world", "🌱", "green", 60),
    ("history", "История", "History", "🏛️", "orange", 70),
    ("geography", "География", "Geography", "🗺️", "teal", 80),
    ("biology", "Биология", "Biology", "🧬", "lime", 90),
    ("physics", "Физика", "Physics", "⚛️", "violet", 100),
    ("chemistry", "Химия", "Chemistry", "🧪", "red", 110),
    ("informatics", "Информатика", "Computer science", "💻", "blue", 120),
    ("social", "Обществоведение", "Social studies", "⚖️", "slate", 130),
    ("pe", "Физическая культура", "Physical education", "🏃", "cyan", 140),
    ("art", "Искусство", "Art", "🎨", "pink", 150),
    ("technology", "Трудовое обучение", "Technology", "🛠️", "stone", 160),
)
COLLEGE_SUBJECTS: tuple[tuple[str, str, str, str, str, int], ...] = (
    (
        "college.programming",
        "Основы программирования",
        "Programming fundamentals",
        "💻",
        "indigo",
        200,
    ),
    ("college.databases", "Базы данных", "Databases", "🗄️", "blue", 210),
    ("college.web", "Веб-технологии", "Web technologies", "🌐", "sky", 220),
    (
        "college.economics",
        "Экономика организации",
        "Business economics",
        "📈",
        "emerald",
        230,
    ),
    (
        "college.accounting",
        "Бухгалтерский учёт",
        "Accounting",
        "🧾",
        "amber",
        240,
    ),
    ("college.taxes", "Налоги и налогообложение", "Taxation", "⚖️", "orange", 250),
)
UNIVERSITY_SUBJECTS: tuple[tuple[str, str, str, str, str, int], ...] = (
    ("uni.calculus", "Математический анализ", "Mathematical analysis", "∫", "violet", 300),
    ("uni.algebra", "Линейная алгебра", "Linear algebra", "🧮", "indigo", 310),
    (
        "uni.algorithms",
        "Алгоритмы и структуры данных",
        "Algorithms and data structures",
        "🧠",
        "blue",
        320,
    ),
    ("uni.databases", "Базы данных", "Databases", "🗄️", "sky", 330),
    ("uni.microeconomics", "Микроэкономика", "Microeconomics", "📉", "emerald", 340),
    ("uni.macroeconomics", "Макроэкономика", "Macroeconomics", "📈", "teal", 350),
    ("uni.finance", "Финансы", "Finance", "💰", "amber", 360),
    ("uni.econometrics", "Эконометрика", "Econometrics", "📊", "orange", 370),
)
MALE_LAST = (
    "Абрамов",
    "Белов",
    "Волков",
    "Громов",
    "Дроздов",
    "Егоров",
    "Жуков",
    "Зайцев",
    "Ильин",
    "Ковалёв",
    "Лебедев",
    "Морозов",
    "Никитин",
    "Орлов",
    "Петров",
    "Романов",
    "Соколов",
    "Тихонов",
    "Фёдоров",
    "Царёв",
)
FEMALE_LAST = (
    "Абрамова",
    "Белова",
    "Волкова",
    "Громова",
    "Дроздова",
    "Егорова",
    "Жукова",
    "Зайцева",
    "Ильина",
    "Ковалёва",
    "Лебедева",
    "Морозова",
    "Никитина",
    "Орлова",
    "Петрова",
    "Романова",
    "Соколова",
    "Тихонова",
    "Фёдорова",
    "Царёва",
)
MALE_FIRST = (
    "Александр",
    "Артём",
    "Богдан",
    "Виктор",
    "Глеб",
    "Даниил",
    "Егор",
    "Иван",
    "Кирилл",
    "Лев",
    "Максим",
    "Никита",
    "Олег",
    "Павел",
    "Роман",
    "Сергей",
    "Тимур",
    "Фёдор",
    "Юрий",
    "Ярослав",
)
FEMALE_FIRST = (
    "Анна",
    "Алина",
    "Валерия",
    "Вера",
    "Дарья",
    "Ева",
    "Екатерина",
    "Елена",
    "Ирина",
    "Ксения",
    "Мария",
    "Наталья",
    "Ольга",
    "Полина",
    "София",
    "Татьяна",
    "Ульяна",
    "Юлия",
)
MALE_MIDDLE = (
    "Александрович",
    "Викторович",
    "Дмитриевич",
    "Игоревич",
    "Максимович",
    "Николаевич",
    "Олегович",
    "Павлович",
    "Сергеевич",
    "Юрьевич",
)
FEMALE_MIDDLE = (
    "Александровна",
    "Викторовна",
    "Дмитриевна",
    "Игоревна",
    "Максимовна",
    "Николаевна",
    "Олеговна",
    "Павловна",
    "Сергеевна",
    "Юрьевна",
)
SCHOOL_SUBJECT_CODES = {
    "primary": ("math", "russian", "world", "pe"),
    "secondary_5_9": ("math", "russian", "english", "history"),
    "secondary_10_11": ("math", "russian", "english", "physics"),
}
COLLEGE_PROGRAMS: tuple[tuple[str, str, str, int, tuple[tuple[str, int, str], ...]], ...] = (
    (
        "09.02.07",
        "Информационные системы и программирование",
        "Программист",
        3,
        (("ИС-11", 1, "А"), ("ИС-21", 2, "А")),
    ),
    (
        "38.02.01",
        "Экономика и бухгалтерский учёт",
        "Бухгалтер",
        2,
        (("ЭК-11", 1, "Б"), ("ЭК-21", 2, "Б")),
    ),
)
UNIVERSITY_PROGRAMS: tuple[
    tuple[str, str, str, int, tuple[tuple[str, int, str], ...]], ...
] = (
    (
        "01.03.02",
        "Прикладная математика и информатика",
        "Бакалавр",
        4,
        (("ПМИ-11", 1, "А"), ("ПМИ-21", 2, "А")),
    ),
    (
        "38.03.01",
        "Экономика",
        "Бакалавр",
        4,
        (("ЭК-11", 1, "Б"), ("ЭК-21", 2, "Б")),
    ),
)
COLLEGE_CURRICULA = {
    "09.02.07": (
        ("ОП.01", "Основы программирования", "discipline", 1, 6, 216, 108, "exam"),
        ("ОП.02", "Базы данных", "discipline", 2, 5, 180, 90, "exam"),
        (
            "ОП.03",
            "Веб-технологии",
            "discipline",
            3,
            5,
            180,
            90,
            "differentiated_credit",
        ),
        ("ОП.04", "Операционные системы", "discipline", 2, 4, 144, 72, "credit"),
        ("ОП.05", "Компьютерные сети", "discipline", 3, 4, 144, 72, "exam"),
        ("ОП.06", "Инженерная графика", "discipline", 1, 3, 108, 54, "credit"),
        (
            "МДК.01",
            "Разработка модулей программного обеспечения",
            "module",
            2,
            6,
            216,
            120,
            "exam",
        ),
        (
            "МДК.02",
            "Разработка и администрирование баз данных",
            "module",
            3,
            6,
            216,
            120,
            "exam",
        ),
        ("ПП.01", "Учебная практика", "practice", 2, 3, 108, 0, "practice_report"),
        (
            "ПП.02",
            "Производственная практика",
            "practice",
            4,
            6,
            216,
            0,
            "practice_report",
        ),
        (
            "КР.01",
            "Курсовая работа по основам программирования",
            "coursework",
            3,
            2,
            72,
            36,
            "coursework",
        ),
        ("ЭК.01", "Экзамен по модулю", "other", 4, 2, 72, 36, "exam"),
        ("ДП.01", "Демонстрационный экзамен", "other", 4, 3, 108, 54, "exam"),
        ("ФК.01", "Физическая культура", "discipline", 1, 3, 108, 54, "credit"),
    ),
    "38.02.01": (
        ("ОП.01", "Экономика организации", "discipline", 1, 6, 216, 108, "exam"),
        ("ОП.02", "Бухгалтерский учёт", "discipline", 2, 6, 216, 108, "exam"),
        (
            "ОП.03",
            "Налоги и налогообложение",
            "discipline",
            3,
            5,
            180,
            90,
            "exam",
        ),
        (
            "ОП.04",
            "Финансы, денежное обращение и кредит",
            "discipline",
            2,
            5,
            180,
            90,
            "differentiated_credit",
        ),
        ("ОП.05", "Аудит", "discipline", 3, 4, 144, 72, "exam"),
        (
            "ОП.06",
            "Информационные технологии в профессиональной деятельности",
            "discipline",
            1,
            3,
            108,
            54,
            "credit",
        ),
        (
            "МДК.01",
            "Практические основы бухгалтерского учёта",
            "module",
            2,
            6,
            216,
            120,
            "exam",
        ),
        (
            "МДК.02",
            "Ведение расчётов с бюджетом",
            "module",
            3,
            5,
            180,
            90,
            "exam",
        ),
        ("ПП.01", "Учебная практика", "practice", 2, 3, 108, 0, "practice_report"),
        (
            "ПП.02",
            "Производственная практика",
            "practice",
            4,
            6,
            216,
            0,
            "practice_report",
        ),
        (
            "КР.01",
            "Курсовая работа по бухгалтерскому учёту",
            "coursework",
            3,
            2,
            72,
            36,
            "coursework",
        ),
        ("ЭК.01", "Квалификационный экзамен", "other", 4, 3, 108, 54, "exam"),
        ("ФК.01", "Физическая культура", "discipline", 1, 3, 108, 54, "credit"),
    ),
}
UNIVERSITY_CURRICULA = {
    "01.03.02": (
        ("Б1.01", "Математический анализ", "discipline", 1, 6, 216, 108, "exam"),
        (
            "Б1.02",
            "Линейная алгебра и аналитическая геометрия",
            "discipline",
            1,
            5,
            180,
            90,
            "exam",
        ),
        ("Б1.03", "Дискретная математика", "discipline", 2, 5, 180, 90, "exam"),
        (
            "Б1.04",
            "Теория вероятностей и математическая статистика",
            "discipline",
            3,
            5,
            180,
            90,
            "exam",
        ),
        (
            "Б1.05",
            "Алгоритмы и структуры данных",
            "discipline",
            2,
            6,
            216,
            108,
            "exam",
        ),
        (
            "Б1.06",
            "Объектно-ориентированное программирование",
            "discipline",
            3,
            5,
            180,
            90,
            "differentiated_credit",
        ),
        ("Б1.07", "Базы данных", "discipline", 4, 5, 180, 90, "exam"),
        (
            "Б1.08",
            "Архитектура вычислительных систем",
            "discipline",
            4,
            4,
            144,
            72,
            "credit",
        ),
        (
            "Б1.09",
            "Веб-программирование",
            "discipline",
            5,
            5,
            180,
            90,
            "exam",
        ),
        ("Б1.10", "Машинное обучение", "discipline", 6, 5, 180, 90, "exam"),
        ("Б2.01", "Учебная практика", "practice", 4, 3, 108, 0, "practice_report"),
        (
            "Б2.02",
            "Производственная практика",
            "practice",
            6,
            6,
            216,
            0,
            "practice_report",
        ),
        (
            "Б3.01",
            "Курсовая работа по алгоритмам",
            "coursework",
            5,
            2,
            72,
            36,
            "coursework",
        ),
        (
            "Б3.02",
            "Выпускная квалификационная работа",
            "other",
            8,
            6,
            216,
            108,
            "exam",
        ),
        (
            "ФТД.01",
            "Иностранный язык в профессиональной сфере",
            "discipline",
            1,
            3,
            108,
            54,
            "credit",
        ),
        ("ФК.01", "Физическая культура", "discipline", 1, 2, 72, 36, "credit"),
    ),
    "38.03.01": (
        ("Б1.01", "Микроэкономика", "discipline", 1, 6, 216, 108, "exam"),
        ("Б1.02", "Макроэкономика", "discipline", 2, 6, 216, 108, "exam"),
        ("Б1.03", "Бухгалтерский учёт", "discipline", 3, 5, 180, 90, "exam"),
        ("Б1.04", "Финансы", "discipline", 4, 5, 180, 90, "exam"),
        (
            "Б1.05",
            "Менеджмент",
            "discipline",
            3,
            5,
            180,
            90,
            "differentiated_credit",
        ),
        ("Б1.06", "Маркетинг", "discipline", 4, 5, 180, 90, "exam"),
        ("Б1.07", "Эконометрика", "discipline", 5, 5, 180, 90, "exam"),
        ("Б1.08", "Статистика", "discipline", 2, 4, 144, 72, "credit"),
        (
            "Б1.09",
            "Налоги и налогообложение",
            "discipline",
            5,
            4,
            144,
            72,
            "exam",
        ),
        ("Б1.10", "Аудит", "discipline", 6, 4, 144, 72, "exam"),
        ("Б2.01", "Учебная практика", "practice", 4, 3, 108, 0, "practice_report"),
        (
            "Б2.02",
            "Производственная практика",
            "practice",
            6,
            6,
            216,
            0,
            "practice_report",
        ),
        (
            "Б3.01",
            "Курсовая работа по экономике",
            "coursework",
            5,
            2,
            72,
            36,
            "coursework",
        ),
        (
            "Б3.02",
            "Выпускная квалификационная работа",
            "other",
            8,
            6,
            216,
            108,
            "exam",
        ),
        (
            "ФТД.01",
            "Иностранный язык в профессиональной сфере",
            "discipline",
            1,
            3,
            108,
            54,
            "credit",
        ),
        ("ФК.01", "Физическая культура", "discipline", 1, 2, 72, 36, "credit"),
    ),
}


@dataclass(frozen=True)
class Person:
    last_name: str
    first_name: str
    middle_name: str

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name} {self.middle_name}"


def _person(index: int) -> Person:
    female = index % 2 == 1
    last = (FEMALE_LAST if female else MALE_LAST)[(index * 7 + 3) % len(MALE_LAST)]
    first = (FEMALE_FIRST if female else MALE_FIRST)[(index * 5 + 1) % len(MALE_FIRST)]
    middle = (FEMALE_MIDDLE if female else MALE_MIDDLE)[
        (index * 3 + 2) % len(MALE_MIDDLE)
    ]
    return Person(last_name=last, first_name=first, middle_name=middle)


_CYRILLIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def _login_slug(value: str) -> str:
    """Turn a human-readable group title into an ASCII login segment."""
    transliterated = value.lower().translate(_CYRILLIC_TO_LATIN)
    cleaned = re.sub(r"[^a-z0-9._@+]+", ".", transliterated)
    return re.sub(r"\.+", ".", cleaned).strip(".")


def _demo_password() -> tuple[str, Path]:
    path = BACKEND_DIR / "secrets" / "pilot_demo_password.txt"
    env_value = os.environ.get("PILOT_DEMO_PASSWORD")
    if env_value:
        return env_value, path
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value, path
    path.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_urlsafe(12)
    path.write_text(value, encoding="utf-8")
    return value, path


async def _repair_demo_logins(session: AsyncSession) -> int:
    """Rename earlier Cyrillic demo logins to ASCII, keeping ids stable."""
    users = list(
        (
            await session.execute(
                select(User).where(User.login.like("demo.%"))
            )
        ).scalars().all()
    )
    changed = 0
    for user in users:
        new_login = _login_slug(user.login)
        if new_login == user.login:
            continue
        user.login = new_login
        if user.email and user.email.lower().endswith("@example.test"):
            user.email = f"{new_login}@example.test"
        changed += 1
    if changed:
        await session.flush()
    return changed


async def _get_or_create_school(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    short_name: str,
    institution_type: str,
    education_levels: list[str],
    city: City,
    address: str,
    phone: str,
    email: str,
) -> tuple[School, bool]:
    school = (
        await session.execute(select(School).where(School.code == code))
    ).scalar_one_or_none()
    created = school is None
    if school is None:
        school = School(
            code=code,
            name=name,
            short_name=short_name,
            institution_type=institution_type,
            education_levels=education_levels,
            city_id=city.id,
            city=city.name,
            address=address,
            phone=phone,
            email=email,
            profile={"data_origin": DEMO_TAG, "pilot": True},
            is_active=True,
        )
        session.add(school)
        await session.flush()
        return school, created

    changed = False
    if school.city_id is None:
        school.city_id = city.id
        changed = True
    if not school.city:
        school.city = city.name
        changed = True
    if not school.address:
        school.address = address
        changed = True
    if not school.phone:
        school.phone = phone
        changed = True
    if not school.email:
        school.email = email
        changed = True
    if not school.institution_type:
        school.institution_type = institution_type
        changed = True
    if not school.education_levels:
        school.education_levels = education_levels
        changed = True
    profile = dict(school.profile or {})
    if profile.get("data_origin") != DEMO_TAG:
        profile.update({"data_origin": DEMO_TAG, "pilot": True})
        school.profile = profile
        changed = True
    if changed:
        await session.flush()
    return school, created


async def _get_or_create_user(
    session: AsyncSession,
    *,
    login: str,
    role: str,
    school_id,
    person: Person,
    password_hash: str,
    parent_code: str | None = None,
) -> tuple[User, bool]:
    user = (
        await session.execute(select(User).where(User.login == login))
    ).scalar_one_or_none()
    if user is not None:
        if (user.preferences or {}).get("data_origin") != DEMO_TAG:
            raise RuntimeError(
                f"login {login!r} is already used by a non-demo account"
            )
        return user, False
    user = User(
        school_id=school_id,
        login=login,
        email=f"{login}@example.test",
        password_hash=password_hash,
        role=role,
        first_name=person.first_name,
        last_name=person.last_name,
        middle_name=person.middle_name,
        parent_code=parent_code,
        preferences={"data_origin": DEMO_TAG, "pilot": True},
        is_active=True,
        is_verified=True,
        must_change_password=False,
    )
    session.add(user)
    await session.flush()
    return user, True


async def _get_or_create_class(
    session: AsyncSession,
    *,
    school: School,
    grade: int,
    letter: str,
    education_level: str,
    academic_year: str,
    title: str | None = None,
    program_id=None,
    course_year: int | None = None,
    homeroom_teacher_id=None,
) -> tuple[SchoolClass, bool]:
    school_class = (
        await session.execute(
            select(SchoolClass).where(
                SchoolClass.school_id == school.id,
                SchoolClass.grade == grade,
                SchoolClass.letter == letter,
                SchoolClass.academic_year == academic_year,
            )
        )
    ).scalar_one_or_none()
    created = school_class is None
    if school_class is None:
        school_class = SchoolClass(
            school_id=school.id,
            grade=grade,
            letter=letter,
            education_level=education_level,
            academic_year=academic_year,
            title=title,
            program_id=program_id,
            course_year=course_year,
            homeroom_teacher_id=homeroom_teacher_id,
            profile={"data_origin": DEMO_TAG, "pilot": True},
            is_active=True,
        )
        session.add(school_class)
        await session.flush()
        return school_class, created
    changed = False
    if title and not school_class.title:
        school_class.title = title
        changed = True
    if program_id and school_class.program_id is None:
        school_class.program_id = program_id
        changed = True
    if course_year is not None and school_class.course_year is None:
        school_class.course_year = course_year
        changed = True
    if homeroom_teacher_id and school_class.homeroom_teacher_id is None:
        school_class.homeroom_teacher_id = homeroom_teacher_id
        changed = True
    if (school_class.profile or {}).get("data_origin") != DEMO_TAG:
        school_class.profile = {
            **(school_class.profile or {}),
            "data_origin": DEMO_TAG,
            "pilot": True,
        }
        changed = True
    if changed:
        await session.flush()
    return school_class, created


async def _get_or_create_program(
    session: AsyncSession,
    *,
    school: School,
    code: str,
    name: str,
    level: str,
    qualification: str,
    duration_years: int,
) -> tuple[EducationProgram, bool]:
    program = (
        await session.execute(
            select(EducationProgram).where(
                EducationProgram.institution_id == school.id,
                EducationProgram.code == code,
            )
        )
    ).scalar_one_or_none()
    created = program is None
    if program is None:
        program = EducationProgram(
            institution_id=school.id,
            code=code,
            name=name,
            education_level=level,
            qualification=qualification,
            duration_years=duration_years,
            profile={
                "data_origin": DEMO_TAG,
                "form": "очная",
                "language": "ru",
            },
            is_active=True,
        )
        session.add(program)
        await session.flush()
    return program, created


async def _ensure_groups(
    session: AsyncSession,
    *,
    school: School,
    admin: User,
) -> tuple[dict[str, UserGroup], dict[tuple, UserGroup]]:
    school_groups: dict[str, UserGroup] = {}
    for category, role_name in ROLE_FOR_CATEGORY.items():
        group = await _get_or_create_group(
            session,
            code=category,
            name=CATEGORY_NAME[category],
            category=category,
            scope_type="school",
            scope_id=school.id,
            parent_id=None,
        )
        if group.parent_id is not None:
            parent = await session.get(UserGroup, group.parent_id)
            if (
                group.scope_type == "school"
                or parent is None
                or parent.category != group.category
            ):
                group.parent_id = None
        school_groups[category] = group
        codes = {
            code
            for code in PERMISSION_BY_CODE
            if legacy_allows(role_name, code)
        }
        await _grant_permissions(session, group, codes, admin)

    classes = list(
        (
            await session.execute(
                select(SchoolClass).where(
                    SchoolClass.school_id == school.id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    class_groups: dict[tuple, UserGroup] = {}
    for school_class in classes:
        for category in ("students", "teachers"):
            group = await _get_or_create_group(
                session,
                code=category,
                name=f"{CATEGORY_NAME[category]} {school_class.display_name}",
                category=category,
                scope_type="class",
                scope_id=school_class.id,
                parent_id=school_groups[category].id,
            )
            class_groups[(school_class.id, category)] = group
    return school_groups, class_groups


async def _attach(
    session: AsyncSession,
    *,
    user: User,
    group: UserGroup | None,
    admin: User,
) -> int:
    if group is None:
        return 0
    return 1 if await _add_membership(session, group, user, admin) else 0


async def _add_class_membership(
    session: AsyncSession,
    *,
    school_class: SchoolClass,
    user: User,
    role_in_class: str = "student",
) -> int:
    existing = (
        await session.execute(
            select(ClassMembership.id).where(
                ClassMembership.class_id == school_class.id,
                ClassMembership.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return 0
    session.add(
        ClassMembership(
            class_id=school_class.id,
            user_id=user.id,
            role_in_class=role_in_class,
            joined_at=JOINED_AT,
        )
    )
    return 1


async def _get_or_create_subject(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    name_en: str,
    icon: str,
    color: str,
    order_index: int,
) -> tuple[Subject, bool]:
    subject = (
        await session.execute(select(Subject).where(Subject.code == code))
    ).scalar_one_or_none()
    created = subject is None
    if subject is None:
        subject = Subject(
            code=code,
            name=name,
            name_i18n={"ru": name, "by": name, "en": name_en},
            icon=icon,
            color=color,
            description=f"Демонстрационный предмет: {name}",
            is_active=True,
            order_index=order_index,
        )
        session.add(subject)
        await session.flush()
    return subject, created


async def _get_or_create_topic(
    session: AsyncSession,
    *,
    subject: Subject,
    grade: int,
) -> tuple[Topic, bool]:
    code = f"{subject.code}.g{grade:02d}"
    topic = (
        await session.execute(select(Topic).where(Topic.code == code))
    ).scalar_one_or_none()
    created = topic is None
    if topic is None:
        topic = Topic(
            subject_id=subject.id,
            class_number=max(1, min(11, grade)),
            code=code,
            title=f"{subject.name}: {grade} класс",
            title_i18n={
                "ru": f"{subject.name}: {grade} класс",
                "by": f"{subject.name}: {grade} клас",
                "en": f"{subject.name}: grade {grade}",
            },
            description=f"Демонстрационная тема по предмету «{subject.name}».",
            icon=subject.icon,
            color=subject.color,
            order_index=grade,
            status="active",
            content=[
                {
                    "type": "text",
                    "title": "Введение",
                    "body": f"Материалы темы для {grade} класса.",
                }
            ],
        )
        session.add(topic)
        await session.flush()
    return topic, created


async def _get_or_create_textbook(
    session: AsyncSession,
    *,
    subject: Subject,
    grade: int,
    title: str,
    uploaded_by: User,
) -> tuple[Textbook, bool]:
    textbook = (
        await session.execute(
            select(Textbook).where(
                Textbook.subject_id == subject.id,
                Textbook.class_number == grade,
                Textbook.title == title,
            )
        )
    ).scalar_one_or_none()
    created = textbook is None
    if textbook is None:
        textbook = Textbook(
            subject_id=subject.id,
            class_number=grade,
            title=title,
            author="Коллектив авторов «ВЕКТОР»",
            publisher="Издательство «ВЕКТОР»",
            year="2026",
            description=f"Демонстрационный учебник: {title}.",
            pages=240,
            uploaded_by=uploaded_by.id,
            status="active",
        )
        session.add(textbook)
        await session.flush()
    return textbook, created


async def _get_or_create_library_item(
    session: AsyncSession,
    *,
    textbook: Textbook,
    subject: Subject,
    grade: int,
    owner: User,
    school_class: SchoolClass,
) -> tuple[LibraryItem, bool]:
    item = (
        await session.execute(
            select(LibraryItem).where(LibraryItem.textbook_id == textbook.id)
        )
    ).scalar_one_or_none()
    created = item is None
    if item is None:
        item = LibraryItem(
            owner_id=owner.id,
            textbook_id=textbook.id,
            subject_id=subject.id,
            class_number=grade,
            title=textbook.title,
            author=textbook.author,
            description=textbook.description,
        )
        session.add(item)
        await session.flush()
    link = (
        await session.execute(
            select(LibraryItemClass.id).where(
                LibraryItemClass.book_id == item.id,
                LibraryItemClass.class_id == school_class.id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        session.add(
            LibraryItemClass(book_id=item.id, class_id=school_class.id)
        )
    return item, created


async def _get_or_create_curriculum(
    session: AsyncSession,
    *,
    school: School,
    program: EducationProgram,
    level: str,
    admin: User,
) -> tuple[EducationCurriculum, bool]:
    name = f"Учебный план {ACADEMIC_YEAR}"
    curriculum = (
        await session.execute(
            select(EducationCurriculum).where(
                EducationCurriculum.program_id == program.id,
                EducationCurriculum.academic_year == ACADEMIC_YEAR,
                EducationCurriculum.name == name,
            )
        )
    ).scalar_one_or_none()
    created = curriculum is None
    if curriculum is None:
        curriculum = EducationCurriculum(
            institution_id=school.id,
            program_id=program.id,
            education_level=level,
            academic_year=ACADEMIC_YEAR,
            name=name,
            description=f"Основной учебный план программы {program.code}.",
            status="approved",
            approved_at=NOW,
            approved_by_id=admin.id,
            profile={
                "data_origin": DEMO_TAG,
                "program_code": program.code,
                "form": "очная",
            },
        )
        session.add(curriculum)
        await session.flush()
    return curriculum, created


async def _add_components(
    session: AsyncSession,
    *,
    curriculum: EducationCurriculum,
    program_code: str,
    components: tuple[tuple, ...],
) -> int:
    existing = {
        code
        for code in (
            await session.execute(
                select(CurriculumComponent.code).where(
                    CurriculumComponent.curriculum_id == curriculum.id
                )
            )
        ).scalars().all()
    }
    created = 0
    for index, row in enumerate(components):
        code, name, kind, semester, credits, hours, contact, assessment = row
        if code in existing:
            continue
        session.add(
            CurriculumComponent(
                curriculum_id=curriculum.id,
                code=code,
                name=name,
                component_type=kind,
                semester=semester,
                credits=credits,
                academic_hours=hours,
                contact_hours=contact,
                assessment_type=assessment,
                is_optional=False,
                order_index=index,
                description=f"Компонент учебного плана {program_code}.",
                details={"data_origin": DEMO_TAG},
            )
        )
        created += 1
    await session.flush()
    return created


async def _ensure_student_profile(
    session: AsyncSession,
    *,
    user: User,
    school: School,
    program: EducationProgram,
    group: SchoolClass,
) -> int:
    existing = (
        await session.execute(
            select(StudentAcademicProfile.id).where(
                StudentAcademicProfile.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return 0
    serial = (
        await session.execute(
            select(func.count()).select_from(StudentAcademicProfile).where(
                StudentAcademicProfile.institution_id == school.id
            )
        )
    ).scalar_one() + 1
    prefix = "К" if school.institution_type == "college" else "У"
    funding = ("budget", "budget", "paid", "target")[serial % 4]
    session.add(
        StudentAcademicProfile(
            user_id=user.id,
            institution_id=school.id,
            program_id=program.id,
            group_id=group.id,
            course_year=group.course_year,
            record_book_number=f"{prefix}-2026-{serial:04d}",
            funding_type=funding,
            enrollment_year=ENROLLMENT_YEAR,
            academic_status="active",
            profile={
                "data_origin": DEMO_TAG,
                "group": group.display_name,
                "program_code": program.code,
            },
        )
    )
    await session.flush()
    return 1


async def _ensure_staff_profile(
    session: AsyncSession,
    *,
    user: User,
    school: School,
    department: str,
    position: str,
    degree: str | None,
    title: str | None,
) -> int:
    existing = (
        await session.execute(
            select(StaffAcademicProfile.id).where(
                StaffAcademicProfile.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return 0
    session.add(
        StaffAcademicProfile(
            user_id=user.id,
            institution_id=school.id,
            department=department,
            position=position,
            academic_degree=degree,
            academic_title=title,
            profile={"data_origin": DEMO_TAG},
        )
    )
    await session.flush()
    return 1


async def _ensure_schedule(
    session: AsyncSession,
    *,
    school_class: SchoolClass,
    subject: Subject,
    teacher: User,
    topic: Topic,
    day_of_week: int,
    lesson_no: int,
) -> tuple[LessonSchedule, int]:
    existing = (
        await session.execute(
            select(LessonSchedule).where(
                LessonSchedule.class_id == school_class.id,
                LessonSchedule.day_of_week == day_of_week,
                LessonSchedule.lesson_no == lesson_no,
                LessonSchedule.valid_from == FIRST_DAY,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, 0
    start_hour = 8 + (lesson_no - 1)
    schedule = LessonSchedule(
        school_id=school_class.school_id,
        class_id=school_class.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        day_of_week=day_of_week,
        lesson_no=lesson_no,
        start_time=time(start_hour, 30),
        end_time=time(start_hour + 1, 15),
        room=f"каб. {10 + lesson_no}",
        topic_id=topic.id,
        note=None,
        valid_from=FIRST_DAY,
        valid_to=LAST_DAY,
    )
    session.add(schedule)
    await session.flush()
    teacher_subject = (
        await session.execute(
            select(TeacherSubject.id).where(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == subject.id,
                TeacherSubject.school_id == school_class.school_id,
                TeacherSubject.class_id == school_class.id,
            )
        )
    ).scalar_one_or_none()
    if teacher_subject is None:
        session.add(
            TeacherSubject(
                teacher_id=teacher.id,
                subject_id=subject.id,
                school_id=school_class.school_id,
                class_id=school_class.id,
                workload_hours=2,
            )
        )
    return schedule, 1


async def _ensure_journal_entries(
    session: AsyncSession,
    *,
    schedules: list[LessonSchedule],
    students_by_class: dict,
) -> int:
    all_dates = {
        date(2026, 10, 19),
        date(2026, 10, 20),
        date(2026, 10, 21),
        date(2026, 10, 26),
        date(2026, 10, 27),
        date(2026, 10, 28),
    }
    school_ids = {schedule.school_id for schedule in schedules}
    existing = {
        tuple(row)
        for row in (
            await session.execute(
                select(
                    JournalEntry.class_id,
                    JournalEntry.subject_id,
                    JournalEntry.student_id,
                    JournalEntry.lesson_date,
                ).where(
                    JournalEntry.school_id.in_(school_ids),
                    JournalEntry.lesson_date.in_(all_dates),
                )
            )
        ).all()
    }
    topic_titles = dict(
        (
            await session.execute(
                select(Topic.id, Topic.title).where(
                    Topic.id.in_(
                        {
                            schedule.topic_id
                            for schedule in schedules
                            if schedule.topic_id is not None
                        }
                    )
                )
            )
        ).all()
    )
    created = 0
    for schedule in schedules:
        students = students_by_class.get(schedule.class_id, [])
        if not students:
            continue
        dates = (
            (date(2026, 10, 19), date(2026, 10, 26))
            if schedule.day_of_week == 1
            else (date(2026, 10, 21), date(2026, 10, 28))
        )
        for lesson_date in dates:
            for index, student in enumerate(students):
                key = (
                    schedule.class_id,
                    schedule.subject_id,
                    student.id,
                    lesson_date,
                )
                if key in existing:
                    continue
                has_grade = (index + schedule.lesson_no) % 5 != 0
                grade = 5 + ((index + schedule.lesson_no + len(student.last_name)) % 6)
                attendance = "present"
                if (index + schedule.lesson_no) % 13 == 0:
                    attendance = "sick"
                elif (index + schedule.lesson_no) % 17 == 0:
                    attendance = "absent"
                elif (index + schedule.lesson_no) % 11 == 0:
                    attendance = "late"
                session.add(
                    JournalEntry(
                        school_id=schedule.school_id,
                        class_id=schedule.class_id,
                        subject_id=schedule.subject_id,
                        teacher_id=schedule.teacher_id,
                        student_id=student.id,
                        lesson_date=lesson_date,
                        lesson_topic=(
                            f"Тема: {topic_titles[schedule.topic_id]}"
                            if schedule.topic_id in topic_titles
                            else None
                        ),
                        grade=grade if has_grade and attendance == "present" else None,
                        attendance=attendance,
                        comment=None,
                    )
                )
                existing.add(key)
                created += 1
    await session.flush()
    return created


async def _ensure_grading_scale(
    session: AsyncSession, school: School, admin: User
) -> int:
    existing = (
        await session.execute(
            select(GradingScale.id).where(GradingScale.school_id == school.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return 0
    session.add(
        GradingScale(
            school_id=school.id,
            subject_id=None,
            scale_type="10_point",
            config={"min": 1, "max": 10, "pass": 4, "data_origin": DEMO_TAG},
        )
    )
    return 1


async def _ensure_quiz(
    session: AsyncSession,
    *,
    school: School,
    school_class: SchoolClass,
    subject: Subject,
    teacher: User,
    students: list[User],
) -> tuple[int, int, int]:
    title = f"Демонстрационный тест: {subject.name}"
    quiz = (
        await session.execute(
            select(Quiz).where(Quiz.school_id == school.id, Quiz.title == title)
        )
    ).scalar_one_or_none()
    created_quiz = 0
    if quiz is None:
        quiz = Quiz(
            title=title,
            quiz_type="test",
            subject_id=subject.id,
            class_number=school_class.grade,
            school_id=school.id,
            created_by=teacher.id,
            time_limit_seconds=600,
            max_attempts=2,
            status="published",
            ai_generated=False,
        )
        session.add(quiz)
        await session.flush()
        created_quiz = 1

    existing_questions = list(
        (
            await session.execute(
                select(Question).where(Question.quiz_id == quiz.id)
            )
        ).scalars().all()
    )
    questions = existing_questions
    created_questions = 0
    if not questions:
        prompts = (
            "Выберите правильный вариант ответа.",
            "Какой раздел относится к теме?",
            "Что является основным понятием?",
        )
        for index, prompt in enumerate(prompts):
            question = Question(
                quiz_id=quiz.id,
                question_type="single_choice",
                prompt=prompt,
                payload={"data_origin": DEMO_TAG},
                points=1,
                order_index=index,
                ai_generated=False,
            )
            session.add(question)
            await session.flush()
            for option_index in range(3):
                session.add(
                    AnswerOption(
                        question_id=question.id,
                        option_text=(
                            f"Вариант {option_index + 1} для вопроса {index + 1}"
                        ),
                        is_correct=option_index == 0,
                        order_index=option_index,
                    )
                )
            questions.append(question)
            created_questions += 1

    assignment = (
        await session.execute(
            select(Assignment).where(
                Assignment.quiz_id == quiz.id,
                Assignment.class_id == school_class.id,
            )
        )
    ).scalar_one_or_none()
    created_assignment = 0
    if assignment is None:
        assignment = Assignment(
            quiz_id=quiz.id,
            assigned_by=teacher.id,
            target_type="class",
            target_id=school_class.id,
            class_id=school_class.id,
            starts_at=NOW,
            due_at=NOW + timedelta(days=7),
            instructions="Демонстрационное задание для проверки модуля оценивания.",
            status="published",
        )
        session.add(assignment)
        await session.flush()
        created_assignment = 1

    created_submissions = 0
    for index, student in enumerate(students[:5]):
        existing_submission = (
            await session.execute(
                select(Submission.id).where(
                    Submission.assignment_id == assignment.id,
                    Submission.student_id == student.id,
                    Submission.attempt_no == 1,
                )
            )
        ).scalar_one_or_none()
        if existing_submission is not None:
            continue
        score = 2 + index % 2
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student.id,
            attempt_no=1,
            status="graded",
            started_at=NOW,
            submitted_at=NOW,
            score=score,
            max_score=len(questions),
            duration_seconds=420 + index * 15,
            answers=[
                {"question_id": str(question.id), "answer": 0}
                for question in questions
            ],
            ai_checked=False,
            teacher_checked=True,
            teacher_comment="Демонстрационная работа проверена.",
            device_id=f"pilot-demo-{index + 1}",
        )
        session.add(submission)
        await session.flush()
        for question_index, question in enumerate(questions):
            session.add(
                Answer(
                    submission_id=submission.id,
                    question_id=question.id,
                    answer_payload={"option": 0},
                    ai_score=None,
                    ai_feedback={"data_origin": DEMO_TAG},
                    teacher_score=1 if question_index < score else 0,
                    teacher_feedback=None,
                    is_correct=question_index < score,
                    answered_at=NOW,
                )
            )
        created_submissions += 1
    return created_quiz, created_questions, created_assignment + created_submissions


async def seed_pilot_data() -> None:
    password, password_path = _demo_password()
    password_hash = hash_password(password)
    credentials: list[tuple[str, str, str, str, str]] = []

    async with AsyncSessionLocal() as session:
        repaired_logins = await _repair_demo_logins(session)
        if repaired_logins:
            print(f"demo logins repaired: {repaired_logins}")

        city = (
            await session.execute(
                select(City).where(City.code == "by.minsk-city.minsk")
            )
        ).scalar_one_or_none()
        if city is None:
            raise RuntimeError("Minsk city is missing; run app.db.seed first")

        school, school_created = await _get_or_create_school(
            session,
            code=settings.seed_school_code,
            name="Пилотная школа «ВЕКТОР»",
            short_name="Пилотная школа",
            institution_type="school",
            education_levels=["primary", "secondary"],
            city=city,
            address="г. Минск, ул. Пилотная, 1",
            phone="+375 17 000-00-01",
            email="school@example.test",
        )
        college, college_created = await _get_or_create_school(
            session,
            code="pilot-college",
            name="Пилотный колледж «ВЕКТОР»",
            short_name="Колледж «ВЕКТОР»",
            institution_type="college",
            education_levels=["vocational"],
            city=city,
            address="г. Минск, ул. Учебная, 12",
            phone="+375 17 000-00-02",
            email="college@example.test",
        )
        university, university_created = await _get_or_create_school(
            session,
            code="pilot-university",
            name="Пилотный университет «ВЕКТОР»",
            short_name="Университет «ВЕКТОР»",
            institution_type="university",
            education_levels=["higher"],
            city=city,
            address="г. Минск, пр-т Независимости, 25",
            phone="+375 17 000-00-03",
            email="university@example.test",
        )

        for code in (
            "primary_education",
            "secondary_education",
            "vocational_education",
            "higher_education",
        ):
            activation = (
                await session.execute(
                    select(ServiceActivation).where(
                        ServiceActivation.service_code == code,
                        ServiceActivation.scope_type == "country",
                        ServiceActivation.scope_id == COUNTRY_SCOPE_ID,
                    )
                )
            ).scalar_one_or_none()
            if activation is not None and not activation.enabled:
                activation.enabled = True

        admin_school, _ = await _get_or_create_user(
            session,
            login="demo.admin.school",
            role="admin",
            school_id=school.id,
            person=_person(901),
            password_hash=password_hash,
        )
        admin_college, _ = await _get_or_create_user(
            session,
            login="demo.admin.college",
            role="admin",
            school_id=college.id,
            person=_person(902),
            password_hash=password_hash,
        )
        admin_university, _ = await _get_or_create_user(
            session,
            login="demo.admin.university",
            role="admin",
            school_id=university.id,
            person=_person(903),
            password_hash=password_hash,
        )
        if not school.director:
            school.director = admin_school.full_name
        if not college.director:
            college.director = admin_college.full_name
        if not university.director:
            university.director = admin_university.full_name

        school_classes = list(
            (
                await session.execute(
                    select(SchoolClass)
                    .where(
                        SchoolClass.school_id == school.id,
                        SchoolClass.academic_year == ACADEMIC_YEAR,
                        SchoolClass.deleted_at.is_(None),
                    )
                    .order_by(SchoolClass.grade, SchoolClass.letter)
                )
            ).scalars().all()
        )
        if not school_classes:
            for grade in range(1, 12):
                school_class, _ = await _get_or_create_class(
                    session,
                    school=school,
                    grade=grade,
                    letter="А",
                    education_level=(
                        "primary" if grade <= 4 else "secondary"
                    ),
                    academic_year=ACADEMIC_YEAR,
                    homeroom_teacher_id=None,
                )
                school_classes.append(school_class)

        school_teachers: list[User] = []
        for index in range(1, 16):
            teacher, _ = await _get_or_create_user(
                session,
                login=f"demo.teacher.school.{index:02d}",
                role="teacher",
                school_id=school.id,
                person=_person(100 + index),
                password_hash=password_hash,
            )
            school_teachers.append(teacher)
        homeroom_teachers = school_teachers[:11]
        subject_teachers = school_teachers[11:15]
        math_teacher, language_teacher, humanities_teacher, science_teacher = (
            subject_teachers
        )

        for index, school_class in enumerate(school_classes):
            teacher = homeroom_teachers[index % len(homeroom_teachers)]
            if school_class.homeroom_teacher_id is None:
                school_class.homeroom_teacher_id = teacher.id
        await session.flush()

        college_teachers: list[User] = []
        for index in range(1, 9):
            teacher, _ = await _get_or_create_user(
                session,
                login=f"demo.teacher.college.{index:02d}",
                role="teacher",
                school_id=college.id,
                person=_person(200 + index),
                password_hash=password_hash,
            )
            college_teachers.append(teacher)
        university_teachers: list[User] = []
        for index in range(1, 9):
            teacher, _ = await _get_or_create_user(
                session,
                login=f"demo.teacher.university.{index:02d}",
                role="teacher",
                school_id=university.id,
                person=_person(300 + index),
                password_hash=password_hash,
            )
            university_teachers.append(teacher)

        college_programs: list[tuple[EducationProgram, tuple[tuple[str, int, str], ...]]] = []
        for code, name, qualification, duration, groups in COLLEGE_PROGRAMS:
            program, _ = await _get_or_create_program(
                session,
                school=college,
                code=code,
                name=name,
                level="vocational",
                qualification=qualification,
                duration_years=duration,
            )
            college_programs.append((program, groups))
        university_programs: list[
            tuple[EducationProgram, tuple[tuple[str, int, str], ...]]
        ] = []
        for code, name, qualification, duration, groups in UNIVERSITY_PROGRAMS:
            program, _ = await _get_or_create_program(
                session,
                school=university,
                code=code,
                name=name,
                level="higher",
                qualification=qualification,
                duration_years=duration,
            )
            university_programs.append((program, groups))

        college_classes: list[tuple[SchoolClass, EducationProgram, User]] = []
        for program_index, (program, groups) in enumerate(college_programs):
            for group_index, (title, course_year, letter) in enumerate(groups):
                curator = college_teachers[
                    (program_index * 2 + group_index) % len(college_teachers)
                ]
                school_class, _ = await _get_or_create_class(
                    session,
                    school=college,
                    grade=course_year,
                    letter=letter,
                    education_level="vocational",
                    academic_year=ACADEMIC_YEAR,
                    title=title,
                    program_id=program.id,
                    course_year=course_year,
                    homeroom_teacher_id=curator.id,
                )
                college_classes.append((school_class, program, curator))
        university_classes: list[tuple[SchoolClass, EducationProgram, User]] = []
        for program_index, (program, groups) in enumerate(university_programs):
            for group_index, (title, course_year, letter) in enumerate(groups):
                curator = university_teachers[
                    (program_index * 2 + group_index) % len(university_teachers)
                ]
                school_class, _ = await _get_or_create_class(
                    session,
                    school=university,
                    grade=course_year,
                    letter=letter,
                    education_level="higher",
                    academic_year=ACADEMIC_YEAR,
                    title=title,
                    program_id=program.id,
                    course_year=course_year,
                    homeroom_teacher_id=curator.id,
                )
                university_classes.append((school_class, program, curator))

        groups_by_school: dict = {}
        class_groups_by_school: dict = {}
        for institution, institution_admin in (
            (school, admin_school),
            (college, admin_college),
            (university, admin_university),
        ):
            groups, class_groups = await _ensure_groups(
                session, school=institution, admin=institution_admin
            )
            groups_by_school[institution.id] = groups
            class_groups_by_school[institution.id] = class_groups

        for institution, institution_admin in (
            (school, admin_school),
            (college, admin_college),
            (university, admin_university),
        ):
            groups = groups_by_school[institution.id]
            await _attach(
                session,
                user=institution_admin,
                group=groups["administration"],
                admin=institution_admin,
            )

        for teacher in school_teachers:
            await _attach(
                session,
                user=teacher,
                group=groups_by_school[school.id]["teachers"],
                admin=admin_school,
            )
        for teacher in college_teachers:
            await _attach(
                session,
                user=teacher,
                group=groups_by_school[college.id]["teachers"],
                admin=admin_college,
            )
            await _ensure_staff_profile(
                session,
                user=teacher,
                school=college,
                department=(
                    "Информационные технологии"
                    if teacher in college_teachers[:4]
                    else "Экономика и управление"
                ),
                position="преподаватель" if teacher not in college_teachers[:2] else "старший преподаватель",
                degree=("магистр" if teacher in college_teachers[:3] else None),
                title=None,
            )
        for teacher in university_teachers:
            await _attach(
                session,
                user=teacher,
                group=groups_by_school[university.id]["teachers"],
                admin=admin_university,
            )
            await _ensure_staff_profile(
                session,
                user=teacher,
                school=university,
                department=(
                    "Прикладная математика и информатика"
                    if teacher in university_teachers[:4]
                    else "Экономика и финансы"
                ),
                position=(
                    "доцент"
                    if teacher in university_teachers[:2]
                    else "старший преподаватель"
                ),
                degree=(
                    "кандидат физико-математических наук"
                    if teacher in university_teachers[:2]
                    else None
                ),
                title="доцент" if teacher in university_teachers[:2] else None,
            )

        school_student_count = 0
        school_students_by_class: dict = {}
        for class_index, school_class in enumerate(school_classes):
            students: list[User] = []
            for index in range(1, 9):
                student, _ = await _get_or_create_user(
                    session,
                    login=(
                        f"demo.pupil."
                        f"{_login_slug(f'{school_class.grade}{school_class.letter}')}."
                        f"{index:02d}"
                    ),
                    role="student",
                    school_id=school.id,
                    person=_person(1000 + class_index * 10 + index),
                    password_hash=password_hash,
                )
                students.append(student)
                await _attach(
                    session,
                    user=student,
                    group=groups_by_school[school.id]["students"],
                    admin=admin_school,
                )
                await _attach(
                    session,
                    user=student,
                    group=class_groups_by_school[school.id][
                        (school_class.id, "students")
                    ],
                    admin=admin_school,
                )
                await _add_class_membership(
                    session, school_class=school_class, user=student
                )
                school_student_count += 1
            school_students_by_class[school_class.id] = students
            await _attach(
                session,
                user=homeroom_teachers[class_index],
                group=class_groups_by_school[school.id][
                    (school_class.id, "teachers")
                ],
                admin=admin_school,
            )

        parent_count = 0
        all_school_students = [
            student
            for students in school_students_by_class.values()
            for student in students
        ]
        for parent_index in range(1, (len(all_school_students) + 3) // 4 + 1):
            parent, _ = await _get_or_create_user(
                session,
                login=f"demo.parent.{parent_index:02d}",
                role="parent",
                school_id=school.id,
                person=_person(2000 + parent_index),
                password_hash=password_hash,
                parent_code=f"P-DEMO-{parent_index:04d}",
            )
            parent_count += 1
            await _attach(
                session,
                user=parent,
                group=groups_by_school[school.id]["parents"],
                admin=admin_school,
            )
            for relation_index, child in enumerate(
                all_school_students[(parent_index - 1) * 4 : parent_index * 4]
            ):
                existing = (
                    await session.execute(
                        select(UserRelation.id).where(
                            UserRelation.parent_id == parent.id,
                            UserRelation.child_id == child.id,
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        UserRelation(
                            parent_id=parent.id,
                            child_id=child.id,
                            relation_type=("mother", "father", "guardian", "other")[
                                relation_index % 4
                            ],
                            is_primary=relation_index == 0,
                            verified_at=NOW,
                        )
                    )

        college_students_by_class: dict = {}
        for class_index, (school_class, program, curator) in enumerate(
            college_classes
        ):
            students: list[User] = []
            for index in range(1, 11):
                student, _ = await _get_or_create_user(
                    session,
                    login=(
                        f"demo.student.college.{_login_slug(school_class.title)}."
                        f"{index:02d}"
                    ),
                    role="student",
                    school_id=college.id,
                    person=_person(3000 + class_index * 20 + index),
                    password_hash=password_hash,
                )
                students.append(student)
                await _attach(
                    session,
                    user=student,
                    group=groups_by_school[college.id]["students"],
                    admin=admin_college,
                )
                await _attach(
                    session,
                    user=student,
                    group=class_groups_by_school[college.id][
                        (school_class.id, "students")
                    ],
                    admin=admin_college,
                )
                await _add_class_membership(
                    session, school_class=school_class, user=student
                )
                await _ensure_student_profile(
                    session,
                    user=student,
                    school=college,
                    program=program,
                    group=school_class,
                )
            college_students_by_class[school_class.id] = students
            await _attach(
                session,
                user=curator,
                group=class_groups_by_school[college.id][
                    (school_class.id, "teachers")
                ],
                admin=admin_college,
            )

        university_students_by_class: dict = {}
        for class_index, (school_class, program, curator) in enumerate(
            university_classes
        ):
            students: list[User] = []
            for index in range(1, 9):
                student, _ = await _get_or_create_user(
                    session,
                    login=(
                        f"demo.student.university.{_login_slug(school_class.title)}."
                        f"{index:02d}"
                    ),
                    role="student",
                    school_id=university.id,
                    person=_person(4000 + class_index * 20 + index),
                    password_hash=password_hash,
                )
                students.append(student)
                await _attach(
                    session,
                    user=student,
                    group=groups_by_school[university.id]["students"],
                    admin=admin_university,
                )
                await _attach(
                    session,
                    user=student,
                    group=class_groups_by_school[university.id][
                        (school_class.id, "students")
                    ],
                    admin=admin_university,
                )
                await _add_class_membership(
                    session, school_class=school_class, user=student
                )
                await _ensure_student_profile(
                    session,
                    user=student,
                    school=university,
                    program=program,
                    group=school_class,
                )
            university_students_by_class[school_class.id] = students
            await _attach(
                session,
                user=curator,
                group=class_groups_by_school[university.id][
                    (school_class.id, "teachers")
                ],
                admin=admin_university,
            )

        subjects: dict[str, Subject] = {}
        for code, name, name_en, icon, color, order in (
            *SCHOOL_SUBJECTS,
            *COLLEGE_SUBJECTS,
            *UNIVERSITY_SUBJECTS,
        ):
            subject, _ = await _get_or_create_subject(
                session,
                code=code,
                name=name,
                name_en=name_en,
                icon=icon,
                color=color,
                order_index=order,
            )
            subjects[code] = subject

        topics: dict[tuple[str, int], Topic] = {}
        for subject in subjects.values():
            if subject.code.startswith("college.") or subject.code.startswith("uni."):
                grades = range(1, 5)
            else:
                grades = range(1, 12)
            for grade in grades:
                topic, _ = await _get_or_create_topic(
                    session, subject=subject, grade=grade
                )
                topics[(subject.code, grade)] = topic

        schedules: list[LessonSchedule] = []
        for class_index, school_class in enumerate(school_classes):
            if school_class.grade <= 4:
                subject_codes = SCHOOL_SUBJECT_CODES["primary"]
            elif school_class.grade <= 9:
                subject_codes = SCHOOL_SUBJECT_CODES["secondary_5_9"]
            else:
                subject_codes = SCHOOL_SUBJECT_CODES["secondary_10_11"]
            for lesson_no, subject_code in enumerate(subject_codes, start=1):
                teacher = homeroom_teachers[class_index]
                if school_class.grade > 4:
                    if subject_code in {"math", "informatics", "physics", "chemistry"}:
                        teacher = math_teacher
                    elif subject_code in {"russian", "belarusian", "literature", "english"}:
                        teacher = language_teacher
                    elif subject_code in {"history", "social"}:
                        teacher = humanities_teacher
                    elif subject_code in {"world", "biology", "geography"}:
                        teacher = science_teacher
                schedule, _ = await _ensure_schedule(
                    session,
                    school_class=school_class,
                    subject=subjects[subject_code],
                    teacher=teacher,
                    topic=topics[(subject_code, school_class.grade)],
                    day_of_week=1,
                    lesson_no=lesson_no,
                )
                schedules.append(schedule)
                for day in (3,):
                    schedule, _ = await _ensure_schedule(
                        session,
                        school_class=school_class,
                        subject=subjects[subject_code],
                        teacher=teacher,
                        topic=topics[(subject_code, school_class.grade)],
                        day_of_week=day,
                        lesson_no=lesson_no,
                    )
                    schedules.append(schedule)

        professional_subjects = {
            "09.02.07": ("college.programming", "college.databases", "college.web"),
            "38.02.01": ("college.economics", "college.accounting", "college.taxes"),
            "01.03.02": ("uni.calculus", "uni.algebra", "uni.algorithms"),
            "38.03.01": ("uni.microeconomics", "uni.macroeconomics", "uni.finance"),
        }
        for school_class, program, curator in (
            *college_classes,
            *university_classes,
        ):
            subject_codes = professional_subjects[program.code]
            teacher_pool = (
                college_teachers
                if school_class.school_id == college.id
                else university_teachers
            )
            for lesson_no, subject_code in enumerate(subject_codes, start=1):
                teacher = teacher_pool[
                    (lesson_no + school_class.grade) % len(teacher_pool)
                ]
                schedule, _ = await _ensure_schedule(
                    session,
                    school_class=school_class,
                    subject=subjects[subject_code],
                    teacher=teacher,
                    topic=topics[(subject_code, school_class.course_year or 1)],
                    day_of_week=2,
                    lesson_no=lesson_no,
                )
                schedules.append(schedule)
                schedule, _ = await _ensure_schedule(
                    session,
                    school_class=school_class,
                    subject=subjects[subject_code],
                    teacher=teacher,
                    topic=topics[(subject_code, school_class.course_year or 1)],
                    day_of_week=4,
                    lesson_no=lesson_no,
                )
                schedules.append(schedule)
                await _attach(
                    session,
                    user=teacher,
                    group=class_groups_by_school[school_class.school_id][
                        (school_class.id, "teachers")
                    ],
                    admin=(
                        admin_college
                        if school_class.school_id == college.id
                        else admin_university
                    ),
                )

        students_by_class = {
            **school_students_by_class,
            **college_students_by_class,
            **university_students_by_class,
        }
        journal_created = await _ensure_journal_entries(
            session, schedules=schedules, students_by_class=students_by_class
        )

        for school_class, program, curator in (
            *college_classes,
            *university_classes,
        ):
            curriculum, _ = await _get_or_create_curriculum(
                session,
                school=(
                    college if school_class.school_id == college.id else university
                ),
                program=program,
                level=(
                    "vocational"
                    if school_class.school_id == college.id
                    else "higher"
                ),
                admin=(
                    admin_college
                    if school_class.school_id == college.id
                    else admin_university
                ),
            )
            components = (
                COLLEGE_CURRICULA[program.code]
                if program.code in COLLEGE_CURRICULA
                else UNIVERSITY_CURRICULA[program.code]
            )
            await _add_components(
                session,
                curriculum=curriculum,
                program_code=program.code,
                components=components,
            )

        curator_by_class: dict = {}
        for index, school_class in enumerate(school_classes):
            curator_by_class[school_class.id] = homeroom_teachers[index]
        for school_class, _, curator in (
            *college_classes,
            *university_classes,
        ):
            curator_by_class[school_class.id] = curator

        library_created = 0
        textbook_created = 0
        recommendations_created = 0
        all_classes = [
            *school_classes,
            *(item[0] for item in college_classes),
            *(item[0] for item in university_classes),
        ]
        for school_class in all_classes:
            if school_class.grade <= 4:
                subject_codes = SCHOOL_SUBJECT_CODES["primary"]
            elif school_class.grade <= 9:
                subject_codes = SCHOOL_SUBJECT_CODES["secondary_5_9"]
            else:
                subject_codes = SCHOOL_SUBJECT_CODES["secondary_10_11"]
            program = None
            if school_class.school_id == college.id:
                program = next(
                    item[1] for item in college_classes if item[0].id == school_class.id
                )
            elif school_class.school_id == university.id:
                program = next(
                    item[1] for item in university_classes if item[0].id == school_class.id
                )
            if program is not None:
                subject_codes = professional_subjects[program.code]
            owner = curator_by_class.get(school_class.id) or (
                admin_college
                if school_class.school_id == college.id
                else admin_university
                if school_class.school_id == university.id
                else admin_school
            )
            for subject_code in subject_codes:
                subject = subjects[subject_code]
                grade = school_class.course_year or school_class.grade
                textbook, created = await _get_or_create_textbook(
                    session,
                    subject=subject,
                    grade=grade,
                    title=(
                        f"{subject.name}. {grade} класс"
                        if school_class.school_id == school.id
                        else f"{subject.name}. {grade} курс"
                    ),
                    uploaded_by=owner,
                )
                textbook_created += 1 if created else 0
                if (subject.code, grade) in topics:
                    existing_link = (
                        await session.execute(
                            select(TextbookTopic.id).where(
                                TextbookTopic.textbook_id == textbook.id,
                                TextbookTopic.topic_id == topics[(subject.code, grade)].id,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing_link is None:
                        session.add(
                            TextbookTopic(
                                textbook_id=textbook.id,
                                topic_id=topics[(subject.code, grade)].id,
                                page_from=1,
                                page_to=24,
                            )
                        )
                item, created = await _get_or_create_library_item(
                    session,
                    textbook=textbook,
                    subject=subject,
                    grade=grade,
                    owner=owner,
                    school_class=school_class,
                )
                library_created += 1 if created else 0
                existing_recommendation = (
                    await session.execute(
                        select(LibraryRecommendation.id).where(
                            LibraryRecommendation.book_id == item.id,
                            LibraryRecommendation.class_id == school_class.id,
                        )
                    )
                ).scalar_one_or_none()
                if existing_recommendation is None:
                    session.add(
                        LibraryRecommendation(
                            teacher_id=owner.id,
                            book_id=item.id,
                            topic_id=(
                                topics[(subject.code, grade)].id
                                if (subject.code, grade) in topics
                                else None
                            ),
                            target_type="class",
                            class_id=school_class.id,
                            note="Рекомендовано для работы на уроках.",
                        )
                    )
                    recommendations_created += 1

        grading_scales_created = 0
        for institution, institution_admin in (
            (school, admin_school),
            (college, admin_college),
            (university, admin_university),
        ):
            grading_scales_created += await _ensure_grading_scale(
                session, institution, institution_admin
            )

        quiz_created = 0
        for institution, institution_admin, school_class, students in (
            (
                school,
                admin_school,
                school_classes[0],
                school_students_by_class[school_classes[0].id],
            ),
            (
                college,
                admin_college,
                college_classes[0][0],
                college_students_by_class[college_classes[0][0].id],
            ),
            (
                university,
                admin_university,
                university_classes[0][0],
                university_students_by_class[university_classes[0][0].id],
            ),
        ):
            subject_code = (
                SCHOOL_SUBJECT_CODES["primary"][0]
                if institution.id == school.id
                else "college.programming"
                if institution.id == college.id
                else "uni.calculus"
            )
            teacher = curator_by_class.get(school_class.id) or institution_admin
            created_quiz, _, _ = await _ensure_quiz(
                session,
                school=institution,
                school_class=school_class,
                subject=subjects[subject_code],
                teacher=teacher,
                students=students,
            )
            quiz_created += created_quiz

        await session.commit()

        demo_users = list(
            (
                await session.execute(
                    select(User)
                    .where(User.login.like("demo.%"))
                    .order_by(User.login)
                )
            ).scalars().all()
        )
        schools_by_id = {
            school.id: school.name,
            college.id: college.name,
            university.id: university.name,
        }
        for user in demo_users:
            credentials.append(
                (
                    user.login,
                    user.role,
                    user.full_name,
                    schools_by_id.get(user.school_id, "—"),
                    password,
                )
            )

        credentials_path = BACKEND_DIR / "secrets" / "pilot_demo_credentials.csv"
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with credentials_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(
                ["login", "role", "full_name", "institution", "password"]
            )
            writer.writerows(credentials)

        print(
            "pilot data: "
            f"schools +{int(school_created) + int(college_created) + int(university_created)}, "
            f"school pupils {school_student_count}, parents {parent_count}, "
            f"college groups {len(college_classes)}, "
            f"university groups {len(university_classes)}, "
            f"journal entries +{journal_created}, "
            f"textbooks +{textbook_created}, library items +{library_created}, "
            f"recommendations +{recommendations_created}, "
            f"grading scales +{grading_scales_created}, quizzes +{quiz_created}"
        )
        print(f"demo password file: {password_path}")
        print(f"demo credentials: {credentials_path}")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(seed_pilot_data())
    except Exception as exc:
        print(f"pilot data failed: {exc}", file=sys.stderr)
        raise
