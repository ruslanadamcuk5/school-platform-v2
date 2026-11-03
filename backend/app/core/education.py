"""Education levels and institution types used across the platform.

The republican platform serves more than a school: primary and secondary
education, vocational (colleges) and higher education.  A level is both a
domain concept and a separately switchable service, so the constants here are
the single source of truth for service codes, labels and permissions.
"""
from __future__ import annotations

from dataclasses import dataclass

PRIMARY = "primary"
SECONDARY = "secondary"
VOCATIONAL = "vocational"
HIGHER = "higher"

EDUCATION_LEVELS: tuple[str, ...] = (PRIMARY, SECONDARY, VOCATIONAL, HIGHER)

LEVEL_LABELS: dict[str, str] = {
    PRIMARY: "Начальное образование",
    SECONDARY: "Среднее образование",
    VOCATIONAL: "Среднее специальное образование",
    HIGHER: "Высшее образование",
}

LEVEL_SHORT_LABELS: dict[str, str] = {
    PRIMARY: "1–4 классы",
    SECONDARY: "5–11 классы",
    VOCATIONAL: "Техникумы и колледжи",
    HIGHER: "Университеты и академии",
}

LEVEL_ICONS: dict[str, str] = {
    PRIMARY: "🎒",
    SECONDARY: "📘",
    VOCATIONAL: "🛠️",
    HIGHER: "🏛️",
}

LEVEL_SERVICE_CODES: dict[str, str] = {
    PRIMARY: "primary_education",
    SECONDARY: "secondary_education",
    VOCATIONAL: "vocational_education",
    HIGHER: "higher_education",
}

SERVICE_CODE_LEVELS: dict[str, str] = {
    code: level for level, code in LEVEL_SERVICE_CODES.items()
}

LEVEL_READ_PERMISSIONS: dict[str, str] = {
    PRIMARY: "primary_education.read",
    SECONDARY: "secondary_education.read",
    VOCATIONAL: "vocational_education.read",
    HIGHER: "higher_education.read",
}

LEVEL_MANAGE_PERMISSIONS: dict[str, str] = {
    PRIMARY: "primary_education.manage",
    SECONDARY: "secondary_education.manage",
    VOCATIONAL: "vocational_education.manage",
    HIGHER: "higher_education.manage",
}

LEVEL_PROGRAM_PERMISSIONS: dict[str, str] = {
    VOCATIONAL: "vocational_education.programs.manage",
    HIGHER: "higher_education.programs.manage",
}

LEVEL_PROFILE_READ_PERMISSIONS: dict[str, str] = {
    VOCATIONAL: "vocational_education.profiles.read",
    HIGHER: "higher_education.profiles.read",
}

LEVEL_PROFILE_MANAGE_PERMISSIONS: dict[str, str] = {
    VOCATIONAL: "vocational_education.profiles.manage",
    HIGHER: "higher_education.profiles.manage",
}

SCHOOL = "school"
COLLEGE = "college"
UNIVERSITY = "university"

INSTITUTION_TYPES: tuple[str, ...] = (SCHOOL, COLLEGE, UNIVERSITY)

INSTITUTION_TYPE_LABELS: dict[str, str] = {
    SCHOOL: "Школа",
    COLLEGE: "Колледж / техникум",
    UNIVERSITY: "Университет / академия",
}

DEFAULT_LEVELS_BY_INSTITUTION_TYPE: dict[str, tuple[str, ...]] = {
    SCHOOL: (PRIMARY, SECONDARY),
    COLLEGE: (VOCATIONAL,),
    UNIVERSITY: (HIGHER,),
}

PROFESSIONAL_LEVELS = frozenset({VOCATIONAL, HIGHER})


@dataclass(frozen=True)
class EducationLevelInfo:
    code: str
    name: str
    short_name: str
    icon: str
    description: str
    service_code: str
    read_permission: str
    manage_permission: str
    program_permission: str | None
    profile_read_permission: str | None
    profile_manage_permission: str | None
    is_professional: bool

    @property
    def payload(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "short_name": self.short_name,
            "icon": self.icon,
            "description": self.description,
            "service_code": self.service_code,
            "read_permission": self.read_permission,
            "manage_permission": self.manage_permission,
            "program_permission": self.program_permission,
            "profile_read_permission": self.profile_read_permission,
            "profile_manage_permission": self.profile_manage_permission,
            "is_professional": self.is_professional,
        }


LEVEL_INFO: dict[str, EducationLevelInfo] = {
    PRIMARY: EducationLevelInfo(
        code=PRIMARY,
        name=LEVEL_LABELS[PRIMARY],
        short_name=LEVEL_SHORT_LABELS[PRIMARY],
        icon=LEVEL_ICONS[PRIMARY],
        description=(
            "Начальная школа: 1–4 классы, первый учитель, базовые навыки, "
            "безопасная адаптация и работа с родителями."
        ),
        service_code=LEVEL_SERVICE_CODES[PRIMARY],
        read_permission=LEVEL_READ_PERMISSIONS[PRIMARY],
        manage_permission=LEVEL_MANAGE_PERMISSIONS[PRIMARY],
        program_permission=None,
        profile_read_permission=None,
        profile_manage_permission=None,
        is_professional=False,
    ),
    SECONDARY: EducationLevelInfo(
        code=SECONDARY,
        name=LEVEL_LABELS[SECONDARY],
        short_name=LEVEL_SHORT_LABELS[SECONDARY],
        icon=LEVEL_ICONS[SECONDARY],
        description=(
            "Средняя школа: 5–11 классы, предметное обучение, профили, "
            "подготовка к экзаменам и профессиональная ориентация."
        ),
        service_code=LEVEL_SERVICE_CODES[SECONDARY],
        read_permission=LEVEL_READ_PERMISSIONS[SECONDARY],
        manage_permission=LEVEL_MANAGE_PERMISSIONS[SECONDARY],
        program_permission=None,
        profile_read_permission=None,
        profile_manage_permission=None,
        is_professional=False,
    ),
    VOCATIONAL: EducationLevelInfo(
        code=VOCATIONAL,
        name=LEVEL_LABELS[VOCATIONAL],
        short_name=LEVEL_SHORT_LABELS[VOCATIONAL],
        icon=LEVEL_ICONS[VOCATIONAL],
        description=(
            "Колледжи и техникумы: специальности, учебные группы, курсы, "
            "производственная практика, зачётные книжки и компетенции."
        ),
        service_code=LEVEL_SERVICE_CODES[VOCATIONAL],
        read_permission=LEVEL_READ_PERMISSIONS[VOCATIONAL],
        manage_permission=LEVEL_MANAGE_PERMISSIONS[VOCATIONAL],
        program_permission=LEVEL_PROGRAM_PERMISSIONS[VOCATIONAL],
        profile_read_permission=LEVEL_PROFILE_READ_PERMISSIONS[VOCATIONAL],
        profile_manage_permission=LEVEL_PROFILE_MANAGE_PERMISSIONS[VOCATIONAL],
        is_professional=True,
    ),
    HIGHER: EducationLevelInfo(
        code=HIGHER,
        name=LEVEL_LABELS[HIGHER],
        short_name=LEVEL_SHORT_LABELS[HIGHER],
        icon=LEVEL_ICONS[HIGHER],
        description=(
            "Университеты и академии: факультеты, кафедры, образовательные "
            "программы, кредиты, академические группы и научная работа."
        ),
        service_code=LEVEL_SERVICE_CODES[HIGHER],
        read_permission=LEVEL_READ_PERMISSIONS[HIGHER],
        manage_permission=LEVEL_MANAGE_PERMISSIONS[HIGHER],
        program_permission=LEVEL_PROGRAM_PERMISSIONS[HIGHER],
        profile_read_permission=LEVEL_PROFILE_READ_PERMISSIONS[HIGHER],
        profile_manage_permission=LEVEL_PROFILE_MANAGE_PERMISSIONS[HIGHER],
        is_professional=True,
    ),
}


def normalize_level(value: str | None) -> str | None:
    """Return a known education level or ``None``."""
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized if normalized in LEVEL_INFO else None


def level_for_grade(grade: int) -> str:
    """Map a school grade to the primary/secondary level."""
    return PRIMARY if 1 <= grade <= 4 else SECONDARY


def default_levels_for_institution(institution_type: str) -> tuple[str, ...]:
    return DEFAULT_LEVELS_BY_INSTITUTION_TYPE.get(
        institution_type, DEFAULT_LEVELS_BY_INSTITUTION_TYPE[SCHOOL]
    )


def level_info(value: str) -> EducationLevelInfo | None:
    return LEVEL_INFO.get(value)
