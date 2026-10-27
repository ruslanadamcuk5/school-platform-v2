"""Organisation API with tenant isolation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep, ensure_school_access
from app.models.org import School, SchoolClass
from app.schemas.org import ClassOut, SchoolOut

router = APIRouter(prefix="/org", tags=["org"])


@router.get(
    "/schools",
    response_model=list[SchoolOut],
    summary="Доступные школы",
)
async def list_schools(current_user: CurrentUser, session: SessionDep):
    stmt = select(School).where(School.deleted_at.is_(None))
    if current_user.role != "superadmin":
        if current_user.school_id is None:
            return []
        stmt = stmt.where(School.id == current_user.school_id)
    stmt = stmt.order_by(School.name)
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/schools/{school_id}",
    response_model=SchoolOut,
    summary="Карточка школы",
)
async def get_school(
    school_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    ensure_school_access(current_user, school_id)
    school = await session.get(School, school_id)
    if school is None or school.deleted_at is not None:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.get(
    "/classes",
    response_model=list[ClassOut],
    summary="Классы школы",
)
async def list_classes(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(default=None),
    grade: int | None = Query(default=None, ge=1, le=11),
):
    tenant_id = ensure_school_access(current_user, school_id)
    stmt = select(SchoolClass).where(
        SchoolClass.school_id == tenant_id,
        SchoolClass.deleted_at.is_(None),
    )
    if grade is not None:
        stmt = stmt.where(SchoolClass.grade == grade)
    stmt = stmt.order_by(SchoolClass.grade, SchoolClass.letter)
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/classes/{class_id}",
    response_model=ClassOut,
    summary="Карточка класса",
)
async def get_class(
    class_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
):
    school_class = await session.get(SchoolClass, class_id)
    if school_class is None or school_class.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Class not found")
    ensure_school_access(current_user, school_class.school_id)
    return school_class
