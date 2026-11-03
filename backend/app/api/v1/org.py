"""Organisation API with tenant isolation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    ensure_school_access,
    require_permission,
)
from app.models.iam import User
from app.models.org import City, Region, School, SchoolClass
from app.schemas.org import (
    CityOut,
    ClassOut,
    RegionOut,
    SchoolCreate,
    SchoolOut,
    SchoolUpdate,
)
from app.services.audit import add_audit_event

router = APIRouter(prefix="/org", tags=["org"])

SCHOOLS_WRITE = require_permission("org.schools.write")


@router.get(
    "/regions",
    response_model=list[RegionOut],
    summary="Области и регионы",
)
async def list_regions(current_user: CurrentUser, session: SessionDep):
    stmt = select(Region).order_by(Region.name)
    return list((await session.execute(stmt)).scalars().all())


@router.get(
    "/cities",
    response_model=list[CityOut],
    summary="Города и районы",
)
async def list_cities(
    current_user: CurrentUser,
    session: SessionDep,
    region_id: uuid.UUID | None = Query(default=None),
):
    stmt = select(City)
    if region_id is not None:
        stmt = stmt.where(City.region_id == region_id)
    stmt = stmt.order_by(City.name)
    return list((await session.execute(stmt)).scalars().all())


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


def _validate_levels(
    institution_type: str, education_levels: list[str]
) -> list[str]:
    allowed = {
        "school": {"primary", "secondary"},
        "college": {"vocational"},
        "university": {"higher"},
    }[institution_type]
    levels = list(dict.fromkeys(education_levels))
    if not set(levels).issubset(allowed):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Institution type '{institution_type}' supports only "
                f"{sorted(allowed)} education levels"
            ),
        )
    return levels


@router.post(
    "/schools",
    response_model=SchoolOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать учреждение образования",
)
async def create_school(
    payload: SchoolCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _: User = Depends(SCHOOLS_WRITE),
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Only the republican administrator can create institutions",
        )
    levels = _validate_levels(payload.institution_type, payload.education_levels)
    exists = (
        await session.execute(select(School.id).where(School.code == payload.code))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=409, detail="Institution with this code already exists"
        )
    if payload.city_id is not None:
        city = await session.get(City, payload.city_id)
        if city is None:
            raise HTTPException(status_code=422, detail="City not found")
    school = School(
        code=payload.code,
        name=payload.name,
        short_name=payload.short_name,
        institution_type=payload.institution_type,
        education_levels=levels,
        city_id=payload.city_id,
        city=payload.city,
        address=payload.address,
        director=payload.director,
        phone=payload.phone,
        email=payload.email,
        profile=payload.profile,
        is_active=payload.is_active,
    )
    session.add(school)
    await session.flush()
    add_audit_event(
        session,
        action="institution_created",
        entity_type="school",
        entity_id=school.id,
        user_id=current_user.id,
        details={
            "code": school.code,
            "institution_type": school.institution_type,
            "education_levels": levels,
        },
    )
    await session.commit()
    await session.refresh(school)
    return school


@router.patch(
    "/schools/{school_id}",
    response_model=SchoolOut,
    summary="Изменить учреждение образования",
)
async def update_school(
    school_id: uuid.UUID,
    payload: SchoolUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    _: User = Depends(SCHOOLS_WRITE),
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Only the republican administrator can change institutions",
        )
    school = await session.get(School, school_id)
    if school is None or school.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Institution not found")
    updates = payload.model_dump(exclude_unset=True)
    institution_type = updates.get("institution_type", school.institution_type)
    levels = updates.get("education_levels")
    if levels is not None:
        updates["education_levels"] = _validate_levels(institution_type, levels)
    elif "institution_type" in updates:
        updates["education_levels"] = _validate_levels(
            institution_type, school.education_levels
        )
    if updates.get("city_id") is not None:
        city = await session.get(City, updates["city_id"])
        if city is None:
            raise HTTPException(status_code=422, detail="City not found")
    for field, value in updates.items():
        setattr(school, field, value)
    add_audit_event(
        session,
        action="institution_updated",
        entity_type="school",
        entity_id=school.id,
        user_id=current_user.id,
        details={"fields": sorted(updates)},
    )
    await session.commit()
    await session.refresh(school)
    return school


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
    education_level: str | None = Query(default=None),
):
    tenant_id = ensure_school_access(current_user, school_id)
    stmt = select(SchoolClass).where(
        SchoolClass.school_id == tenant_id,
        SchoolClass.deleted_at.is_(None),
    )
    if grade is not None:
        stmt = stmt.where(SchoolClass.grade == grade)
    if education_level is not None:
        stmt = stmt.where(SchoolClass.education_level == education_level)
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
