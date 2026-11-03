"""Analytics API: school overview, subject/class slices and CSV export."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    SessionDep,
    ensure_school_access,
    require_permission,
    require_service,
)
from app.core.config import settings
from app.models.iam import User
from app.models.journal import JournalEntry
from app.models.lms import Subject
from app.models.org import ClassMembership, School, SchoolClass
from app.schemas.analytics import (
    AnalyticsAttendanceOut,
    AnalyticsClassOut,
    AnalyticsGradesOut,
    AnalyticsOverviewOut,
    AnalyticsSubjectOut,
    AnalyticsTotalsOut,
)
from app.services.audit import add_audit_event

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_service("analytics"))],
)

ANALYTICS_READ = require_permission(
    "analytics.reports.read",
    "analytics.bi.read",
)
ANALYTICS_EXPORT = require_permission("analytics.reports.export")

ATTENDED_VALUES = ("present", "late")
GRADE_BUCKETS = range(1, 11)


def _percent(part: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(part * 100 / total, 1)


def _average(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if any(char in text for char in ',;"\n\r'):
        return '"' + text.replace('"', '""') + '"'
    return text


def build_class_csv(overview: AnalyticsOverviewOut) -> str:
    """Render the class slice as an Excel-friendly CSV document."""
    rows: list[list[object]] = [
        ["Школа", overview.school_name],
        ["Учебный год", overview.academic_year],
        [],
        [
            "Класс",
            "Учеников",
            "Оценок",
            "Средний балл",
            "Посещаемость, %",
        ],
    ]
    for item in overview.classes:
        rows.append(
            [
                item.class_name,
                item.students,
                item.grades_count,
                item.average if item.average is not None else "",
                item.attendance_rate if item.attendance_rate is not None else "",
            ]
        )
    return "\n".join(",".join(_csv_cell(cell) for cell in row) for row in rows) + "\n"


async def _build_overview(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    academic_year: str | None,
) -> AnalyticsOverviewOut:
    school = await session.get(School, tenant_id)
    if school is None or school.deleted_at is not None:
        raise HTTPException(status_code=404, detail="School not found")

    year_rows = (
        await session.execute(
            select(SchoolClass.academic_year)
            .where(
                SchoolClass.school_id == tenant_id,
                SchoolClass.deleted_at.is_(None),
            )
            .distinct()
            .order_by(SchoolClass.academic_year.desc())
        )
    ).scalars().all()
    available_years = [year for year in year_rows if year]
    year = academic_year or (
        available_years[0] if available_years else settings.seed_academic_year
    )

    classes = (
        await session.execute(
            select(SchoolClass)
            .where(
                SchoolClass.school_id == tenant_id,
                SchoolClass.deleted_at.is_(None),
                SchoolClass.academic_year == year,
            )
            .order_by(SchoolClass.grade, SchoolClass.letter)
        )
    ).scalars().all()
    class_ids = [item.id for item in classes]

    role_rows = (
        await session.execute(
            select(User.role, func.count())
            .where(
                User.school_id == tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .group_by(User.role)
        )
    ).all()
    role_counts = {role: count for role, count in role_rows}

    students_by_class: dict[uuid.UUID, int] = {}
    if class_ids:
        student_rows = (
            await session.execute(
                select(ClassMembership.class_id, func.count())
                .where(
                    ClassMembership.class_id.in_(class_ids),
                    ClassMembership.left_at.is_(None),
                    ClassMembership.role_in_class == "student",
                )
                .group_by(ClassMembership.class_id)
            )
        ).all()
        students_by_class = {class_id: count for class_id, count in student_rows}

    entry_conditions = [
        JournalEntry.school_id == tenant_id,
        JournalEntry.class_id.in_(class_ids),
    ]

    grade_distribution: dict[int, int] = {}
    average_grade: float | None = None
    grades_count = 0
    attendance = AnalyticsAttendanceOut()

    subject_rows: list[AnalyticsSubjectOut] = []
    class_stats: dict[uuid.UUID, tuple[int, float | None, int, float | None]] = {}

    if class_ids:
        grade_rows = (
            await session.execute(
                select(JournalEntry.grade, func.count())
                .where(*entry_conditions, JournalEntry.grade.is_not(None))
                .group_by(JournalEntry.grade)
            )
        ).all()
        grade_distribution = {
            int(grade): count for grade, count in grade_rows if grade is not None
        }
        grades_count = sum(grade_distribution.values())
        for grade in GRADE_BUCKETS:
            grade_distribution.setdefault(grade, 0)

        avg_row = (
            await session.execute(
                select(
                    func.avg(JournalEntry.grade),
                    func.count(JournalEntry.grade),
                ).where(*entry_conditions)
            )
        ).one()
        average_grade = _average(avg_row[0])

        attendance_rows = (
            await session.execute(
                select(JournalEntry.attendance, func.count())
                .where(*entry_conditions)
                .group_by(JournalEntry.attendance)
            )
        ).all()
        attendance_counts = {
            status: count for status, count in attendance_rows if status is not None
        }
        attendance_total = sum(attendance_counts.values())
        attended = sum(
            attendance_counts.get(status, 0) for status in ATTENDED_VALUES
        )
        attendance = AnalyticsAttendanceOut(
            total=attendance_total,
            present=attendance_counts.get("present", 0),
            absent=attendance_counts.get("absent", 0),
            sick=attendance_counts.get("sick", 0),
            late=attendance_counts.get("late", 0),
            excused=attendance_counts.get("excused", 0),
            rate=_percent(attended, attendance_total),
        )

        subject_rows_raw = (
            await session.execute(
                select(
                    Subject.id,
                    Subject.name,
                    func.count(JournalEntry.grade),
                    func.avg(JournalEntry.grade),
                    func.count(JournalEntry.id),
                    func.sum(
                        case(
                            (JournalEntry.attendance.in_(ATTENDED_VALUES), 1),
                            else_=0,
                        )
                    ),
                )
                .join(Subject, Subject.id == JournalEntry.subject_id)
                .where(*entry_conditions)
                .group_by(Subject.id, Subject.name)
                .order_by(
                    func.coalesce(func.avg(JournalEntry.grade), 0).desc(),
                    Subject.name,
                )
                .limit(12)
            )
        ).all()
        subject_rows = [
            AnalyticsSubjectOut(
                subject_id=subject_id,
                subject_name=subject_name,
                grades_count=int(subject_grades or 0),
                average=_average(subject_average),
                attendance_total=int(subject_attendance_total or 0),
                attendance_rate=_percent(
                    int(attended_count or 0), int(subject_attendance_total or 0)
                ),
            )
            for (
                subject_id,
                subject_name,
                subject_grades,
                subject_average,
                subject_attendance_total,
                attended_count,
            ) in subject_rows_raw
        ]

        class_rows_raw = (
            await session.execute(
                select(
                    JournalEntry.class_id,
                    func.count(JournalEntry.grade),
                    func.avg(JournalEntry.grade),
                    func.count(JournalEntry.id),
                    func.sum(
                        case(
                            (JournalEntry.attendance.in_(ATTENDED_VALUES), 1),
                            else_=0,
                        )
                    ),
                )
                .where(*entry_conditions)
                .group_by(JournalEntry.class_id)
            )
        ).all()
        class_stats = {
            class_id: (
                int(class_grades or 0),
                _average(class_average),
                int(class_attendance_total or 0),
                _percent(int(attended_count or 0), int(class_attendance_total or 0)),
            )
            for (
                class_id,
                class_grades,
                class_average,
                class_attendance_total,
                attended_count,
            ) in class_rows_raw
        }

    class_items: list[AnalyticsClassOut] = []
    for school_class in classes:
        class_grades, class_average, class_total, class_rate = class_stats.get(
            school_class.id, (0, None, 0, None)
        )
        class_items.append(
            AnalyticsClassOut(
                class_id=school_class.id,
                class_name=school_class.display_name,
                grade=school_class.grade,
                letter=school_class.letter,
                students=students_by_class.get(school_class.id, 0),
                grades_count=class_grades,
                average=class_average,
                attendance_total=class_total,
                attendance_rate=class_rate,
            )
        )

    excellent = sum(
        count for grade, count in grade_distribution.items() if grade >= 9
    )
    good = sum(count for grade, count in grade_distribution.items() if 7 <= grade <= 8)
    satisfactory = sum(
        count for grade, count in grade_distribution.items() if 4 <= grade <= 6
    )
    low = sum(count for grade, count in grade_distribution.items() if grade <= 3)

    return AnalyticsOverviewOut(
        school_id=school.id,
        school_name=school.name,
        academic_year=year,
        available_years=available_years,
        generated_at=datetime.now(timezone.utc),
        totals=AnalyticsTotalsOut(
            students=role_counts.get("student", 0),
            teachers=role_counts.get("teacher", 0),
            classes=len(classes),
            grades_count=grades_count,
        ),
        grades=AnalyticsGradesOut(
            average=average_grade,
            distribution=grade_distribution,
            excellent=excellent,
            good=good,
            satisfactory=satisfactory,
            low=low,
        ),
        attendance=attendance,
        subjects=subject_rows,
        classes=class_items,
    )


@router.get(
    "/overview",
    response_model=AnalyticsOverviewOut,
    summary="Сводная аналитика школы",
)
async def overview(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    academic_year: str | None = Query(default=None, pattern=r"^\d{4}/\d{4}$"),
    _: User = Depends(ANALYTICS_READ),
):
    tenant_id = ensure_school_access(current_user, school_id)
    return await _build_overview(session, tenant_id, academic_year)


@router.get(
    "/export.csv",
    summary="Выгрузка аналитики школы в CSV",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_csv(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    academic_year: str | None = Query(default=None, pattern=r"^\d{4}/\d{4}$"),
    _: User = Depends(ANALYTICS_EXPORT),
):
    tenant_id = ensure_school_access(current_user, school_id)
    payload = await _build_overview(session, tenant_id, academic_year)
    add_audit_event(
        session,
        action="analytics_report_exported",
        entity_type="analytics_report",
        entity_id=tenant_id,
        school_id=tenant_id,
        user_id=current_user.id,
        details={
            "academic_year": payload.academic_year,
            "format": "csv",
            "classes": len(payload.classes),
        },
    )
    await session.commit()
    content = "\ufeff" + build_class_csv(payload)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="analytics-report.csv"',
        },
    )
