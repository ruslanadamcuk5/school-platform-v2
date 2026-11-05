"""Safety API: psychological support appeals, incidents, geolocation and consents.

Access rules (multi-tenant, per school):
- Users may only see/create their own appeals and geolocation points.
- Parents may act on behalf of their linked children.
- Psychologists/administrators/secretaries see school-wide data for their school.
- Cross-school access returns 403; foreign records return 404.
- Geolocation requires an active consent from the legal representative.
- Consent may be revoked at any time; processing stops within 15 calendar days
  (Law of the Republic of Belarus No. 99-З of 07.05.2021, Art. 10).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    TenantSchoolId,
    require_permission,
    require_service,
)
from app.models.iam import User, UserRelation
from app.models.org import School
from app.models.safety import (
    Consent,
    GeolocationPoint,
    Incident,
    SupportAppeal,
)
from app.models.system import Setting
from app.schemas.safety import (
    ConsentCreate,
    ConsentOut,
    ConsentRevoke,
    GeolocationPointCreate,
    GeolocationPointOut,
    IncidentCreate,
    IncidentOut,
    IncidentResolve,
    SafetyPurgeResult,
    SafetySettings,
    SafetySettingsUpdate,
    SupportAppealCreate,
    SupportAppealOut,
    SupportAppealRespond,
)
from app.services.audit import add_audit_event

router = APIRouter(
    prefix="/safety",
    tags=["safety"],
    dependencies=[Depends(require_service("safety"))],
)

APPEALS_USE = require_permission("safety.support.use")
APPEALS_MANAGE = require_permission("safety.incidents.manage")
INCIDENTS_READ = require_permission("safety.incidents.read")
INCIDENTS_MANAGE = require_permission("safety.incidents.manage")
GEO_READ = require_permission("safety.geolocation.read")
CONSENTS_MANAGE = require_permission("safety.consents.manage")
SETTINGS_READ = require_permission("safety.incidents.read", "safety.settings.manage")
SETTINGS_MANAGE = require_permission("safety.settings.manage")

SAFETY_SETTINGS_KEY = "safety.settings"
DEFAULT_SAFETY_SETTINGS = {
    "retention_days": 365,
    "incident_retention_days": 1095,
    "consent_age_threshold": 16,
    "allow_anonymous_appeals": True,
    "geolocation_enabled": True,
}

RequesterStatus = Literal["student", "parent", "staff", "superadmin"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_on(dob: date | None, today: date) -> int | None:
    if dob is None:
        return None
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _is_minor(dob: date | None, threshold: int) -> bool:
    """Return True when the student is below the consent age threshold.

    Unknown date of birth is treated as a minor (strict default) because
    special personal data of children must be protected.
    """
    age = _age_on(dob, date.today())
    if age is None:
        return True
    return age < threshold


async def _load_safety_settings(
    session: SessionDep, school_id: uuid.UUID | None = None
) -> dict:
    """Merge global defaults with an optional per-school override."""
    merged = dict(DEFAULT_SAFETY_SETTINGS)
    global_setting = await session.get(Setting, SAFETY_SETTINGS_KEY)
    if global_setting is not None and isinstance(global_setting.value, dict):
        merged.update(
            {k: v for k, v in global_setting.value.items() if k in merged}
        )
    if school_id is not None:
        override = await session.get(
            Setting, f"{SAFETY_SETTINGS_KEY}:{school_id}"
        )
        if override is not None and isinstance(override.value, dict):
            merged.update({k: v for k, v in override.value.items() if k in merged})
    return merged


def _settings_scope(
    current_user: CurrentUser, school_id: uuid.UUID | None
) -> uuid.UUID | None:
    """Superadmin may edit global or a school's settings; others only own school."""
    if current_user.role == "superadmin":
        return school_id
    return current_user.school_id



async def _get_school(session: SessionDep, school_id: uuid.UUID) -> None:
    if await session.get(School, school_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )


async def _resolve_school_id(
    current_user: CurrentUser,
    payload_school_id: uuid.UUID | None,
) -> uuid.UUID:
    if current_user.role == "superadmin":
        if payload_school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required for superadmin",
            )
        return payload_school_id
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School context is required",
        )
    if payload_school_id is not None and payload_school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another school",
        )
    return current_user.school_id


async def _assert_student_in_school(
    session: SessionDep,
    school_id: uuid.UUID,
    student_id: uuid.UUID,
) -> User:
    student = await session.get(User, student_id)
    if (
        student is None
        or student.deleted_at is not None
        or student.role != "student"
        or student.school_id != school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student not found in this school",
        )
    return student


async def _assert_parent_link(
    session: SessionDep,
    parent_id: uuid.UUID,
    child_id: uuid.UUID,
) -> None:
    relation = await session.scalar(
        select(UserRelation.id).where(
            UserRelation.parent_id == parent_id,
            UserRelation.child_id == child_id,
        )
    )
    if relation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student is not linked to this parent",
        )


def _user_requester_role(current_user: CurrentUser) -> RequesterStatus:
    if current_user.role == "superadmin":
        return "superadmin"
    if current_user.role == "student":
        return "student"
    if current_user.role == "parent":
        return "parent"
    return "staff"


async def _assert_appeal_requester_access(
    session: SessionDep,
    current_user: CurrentUser,
    school_id: uuid.UUID,
    student_id: uuid.UUID | None,
    requester_id: uuid.UUID | None,
) -> None:
    role = _user_requester_role(current_user)
    if role == "superadmin":
        return
    if student_id is not None:
        await _assert_student_in_school(session, school_id, student_id)
    if role == "student":
        if student_id is not None and student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student can only create appeals for themselves",
            )
        if requester_id is not None and requester_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student can only create appeals as themselves",
            )
    elif role == "parent":
        if student_id is not None:
            await _assert_parent_link(session, current_user.id, student_id)
        if requester_id is not None and requester_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Parent can only create appeals as themselves",
            )


async def _assert_geolocation_requester_access(
    session: SessionDep,
    current_user: CurrentUser,
    school_id: uuid.UUID,
    student_id: uuid.UUID,
    requester_id: uuid.UUID | None,
) -> None:
    await _assert_student_in_school(session, school_id, student_id)
    role = _user_requester_role(current_user)
    if role == "superadmin":
        return
    if role == "student" and student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student can only register geolocation for themselves",
        )
    if role == "parent":
        await _assert_parent_link(session, current_user.id, student_id)
    if requester_id is not None and requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester mismatch",
        )


async def _assert_active_geolocation_consent(
    session: SessionDep,
    student_id: uuid.UUID,
) -> Consent:
    """Return an active consent for geolocation scope, or raise 403.

    Under Law No. 99-З Art. 5/8, special personal data processing requires
    consent of the subject or their legal representative.
    """
    now = _now()
    consent = await session.scalar(
        select(Consent).where(
            Consent.student_id == student_id,
            Consent.scope == "geolocation",
            Consent.granted == True,  # noqa: E712
            Consent.deleted_at.is_(None),
            (Consent.revoked_at.is_(None)),
            (Consent.expires_at.is_(None) | (Consent.expires_at > now)),
        )
    )
    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active geolocation consent for this student",
        )
    return consent


@router.get("/appeals/mine", response_model=list[SupportAppealOut])
async def list_my_appeals(
    current_user: CurrentUser,
    session: SessionDep,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(APPEALS_USE),
) -> list[SupportAppeal]:
    statement = select(SupportAppeal).where(
        SupportAppeal.deleted_at.is_(None),
        SupportAppeal.requester_id == current_user.id,
    )
    if status_filter is not None:
        statement = statement.where(SupportAppeal.status == status_filter)
    statement = (
        statement.order_by(SupportAppeal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.get("/appeals", response_model=list[SupportAppealOut])
async def list_school_appeals(
    school_id: TenantSchoolId,
    session: SessionDep,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(APPEALS_MANAGE),
) -> list[SupportAppeal]:
    statement = select(SupportAppeal).where(
        SupportAppeal.deleted_at.is_(None),
        SupportAppeal.school_id == school_id,
    )
    if status_filter is not None:
        statement = statement.where(SupportAppeal.status == status_filter)
    statement = (
        statement.order_by(SupportAppeal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post(
    "/appeals",
    response_model=SupportAppealOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_appeal(
    payload: SupportAppealCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(APPEALS_USE),
) -> SupportAppeal:
    school_id = await _resolve_school_id(current_user, payload.school_id)
    await _get_school(session, school_id)
    safety_settings = await _load_safety_settings(session, school_id)

    if payload.is_anonymous:
        if not safety_settings["allow_anonymous_appeals"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anonymous appeals are disabled for this school",
            )
        # Anonymous appeals carry no identity link (Law No. 99-З, data minimisation).
        if payload.consent_required and not payload.consent_given:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consent is required to process this appeal",
            )
        appeal = SupportAppeal(
            school_id=school_id,
            student_id=None,
            requester_id=None,
            category=payload.category,
            priority=payload.priority,
            status="open",
            subject=payload.subject,
            message=payload.message,
            consent_required=payload.consent_required,
            consent_given=payload.consent_given,
            is_anonymous=True,
        )
    else:
        await _assert_appeal_requester_access(
            session, current_user, school_id, payload.student_id, current_user.id
        )
        if payload.student_id is not None:
            student = await _assert_student_in_school(
                session, school_id, payload.student_id
            )
            threshold = int(safety_settings["consent_age_threshold"])
            if _is_minor(student.date_of_birth, threshold) and not payload.consent_required:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Consent cannot be waived for a minor",
                )
        if payload.consent_required and not payload.consent_given:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consent is required to process this appeal",
            )
        appeal = SupportAppeal(
            school_id=school_id,
            student_id=payload.student_id,
            requester_id=current_user.id,
            category=payload.category,
            priority=payload.priority,
            status="open",
            subject=payload.subject,
            message=payload.message,
            consent_required=payload.consent_required,
            consent_given=payload.consent_given,
            is_anonymous=False,
        )
    session.add(appeal)
    await session.flush()
    add_audit_event(
        session,
        action="safety.appeal.create",
        entity_type="safety.appeal",
        entity_id=appeal.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "category": appeal.category,
            "student_id": str(appeal.student_id) if appeal.student_id else None,
            "is_anonymous": appeal.is_anonymous,
        },
    )
    await session.commit()
    await session.refresh(appeal)
    return appeal


@router.post(
    "/appeals/{appeal_id}/respond",
    response_model=SupportAppealOut,
)
async def respond_appeal(
    appeal_id: uuid.UUID,
    payload: SupportAppealRespond,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(APPEALS_MANAGE),
) -> SupportAppeal:
    appeal = await session.get(SupportAppeal, appeal_id)
    if appeal is None or appeal.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found",
        )
    if (
        current_user.role != "superadmin"
        and appeal.school_id is not None
        and appeal.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot respond to an appeal from another school",
        )
    if appeal.status not in ("open", "in_progress"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appeal is already closed",
        )

    appeal.response = payload.response
    appeal.status = payload.status
    appeal.responded_by_id = current_user.id
    appeal.responded_at = _now()
    if payload.status == "closed":
        appeal.closed_at = _now()
    add_audit_event(
        session,
        action="safety.appeal.respond",
        entity_type="safety.appeal",
        entity_id=appeal.id,
        school_id=appeal.school_id,
        user_id=current_user.id,
        details={"status": appeal.status},
    )
    await session.commit()
    await session.refresh(appeal)
    return appeal


@router.post(
    "/appeals/{appeal_id}/close",
    response_model=SupportAppealOut,
)
async def close_appeal(
    appeal_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(APPEALS_MANAGE),
) -> SupportAppeal:
    appeal = await session.get(SupportAppeal, appeal_id)
    if appeal is None or appeal.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found",
        )
    if (
        current_user.role != "superadmin"
        and appeal.school_id is not None
        and appeal.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot close an appeal from another school",
        )
    if appeal.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appeal is already closed",
        )

    appeal.status = "closed"
    appeal.closed_at = _now()
    add_audit_event(
        session,
        action="safety.appeal.close",
        entity_type="safety.appeal",
        entity_id=appeal.id,
        school_id=appeal.school_id,
        user_id=current_user.id,
        details={"status": appeal.status},
    )
    await session.commit()
    await session.refresh(appeal)
    return appeal


@router.get("/incidents", response_model=list[IncidentOut])
async def list_school_incidents(
    school_id: TenantSchoolId,
    session: SessionDep,
    status_filter: str | None = Query(None, alias="status"),
    severity_filter: str | None = Query(None, alias="severity"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(INCIDENTS_READ),
) -> list[Incident]:
    statement = select(Incident).where(
        Incident.deleted_at.is_(None),
        Incident.school_id == school_id,
    )
    if status_filter is not None:
        statement = statement.where(Incident.status == status_filter)
    if severity_filter is not None:
        statement = statement.where(Incident.severity == severity_filter)
    statement = (
        statement.order_by(Incident.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post(
    "/incidents",
    response_model=IncidentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    payload: IncidentCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(INCIDENTS_MANAGE),
) -> Incident:
    school_id = await _resolve_school_id(current_user, payload.school_id)
    await _get_school(session, school_id)

    incident = Incident(
        school_id=school_id,
        category=payload.category,
        severity=payload.severity,
        title=payload.title,
        description=payload.description,
        reported_by_id=current_user.id,
        status="open",
    )
    session.add(incident)
    await session.flush()
    add_audit_event(
        session,
        action="safety.incident.create",
        entity_type="safety.incident",
        entity_id=incident.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "category": incident.category,
            "severity": incident.severity,
        },
    )
    await session.commit()
    await session.refresh(incident)
    return incident


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=IncidentOut,
)
async def resolve_incident(
    incident_id: uuid.UUID,
    payload: IncidentResolve,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(INCIDENTS_MANAGE),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None or incident.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )
    if (
        current_user.role != "superadmin"
        and incident.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot resolve an incident from another school",
        )
    if incident.status not in ("open", "investigating"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is already closed",
        )

    incident.actions_taken = payload.actions_taken
    incident.status = payload.status
    incident.resolved_by_id = current_user.id
    incident.resolved_at = _now()
    add_audit_event(
        session,
        action="safety.incident.resolve",
        entity_type="safety.incident",
        entity_id=incident.id,
        school_id=incident.school_id,
        user_id=current_user.id,
        details={"status": incident.status},
    )
    await session.commit()
    await session.refresh(incident)
    return incident


@router.get("/consents", response_model=list[ConsentOut])
async def list_consents(
    school_id: TenantSchoolId,
    session: SessionDep,
    scope_filter: str | None = Query(None, alias="scope"),
    student_id: uuid.UUID | None = Query(None, alias="student_id"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(CONSENTS_MANAGE),
) -> list[Consent]:
    statement = select(Consent).where(
        Consent.deleted_at.is_(None),
    )
    if student_id is not None:
        student = await session.get(User, student_id)
        if (
            student is None
            or student.deleted_at is not None
            or student.role != "student"
            or student.school_id != school_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student not found in this school",
            )
        statement = statement.where(Consent.student_id == student_id)
    else:
        # Filter consents whose student belongs to the school.
        statement = statement.join(
            User, User.id == Consent.student_id
        ).where(User.school_id == school_id)
    if scope_filter is not None:
        statement = statement.where(Consent.scope == scope_filter)
    statement = (
        statement.order_by(Consent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post(
    "/consents",
    response_model=ConsentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_consent(
    payload: ConsentCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(CONSENTS_MANAGE),
) -> Consent:
    # The student must belong to the actor's school scope.
    school_id = await _resolve_school_id(
        current_user,
        payload.school_id,
    )
    student = await _assert_student_in_school(
        session, school_id, payload.student_id
    )
    safety_settings = await _load_safety_settings(session, school_id)
    threshold = int(safety_settings["consent_age_threshold"])
    minor = _is_minor(student.date_of_birth, threshold)

    if minor:
        # A minor under the consent age acts through a legal representative
        # (Law No. 99-З, Art. 5(8)).
        if payload.legal_representative_id == payload.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A minor cannot give consent on their own behalf",
            )
        await _assert_parent_link(
            session, payload.legal_representative_id, payload.student_id
        )

    # Legal representative must be an active user of the same school.
    rep = await session.get(User, payload.legal_representative_id)
    if (
        rep is None
        or rep.deleted_at is not None
        or rep.school_id != school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Legal representative not found in this school",
        )

    existing = await session.scalar(
        select(Consent).where(
            Consent.student_id == payload.student_id,
            Consent.scope == payload.scope,
            Consent.deleted_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent for this scope already exists",
        )

    consent = Consent(
        student_id=payload.student_id,
        legal_representative_id=payload.legal_representative_id,
        scope=payload.scope,
        granted=payload.granted,
        granted_at=_now() if payload.granted else None,
        source=payload.source,
        expires_at=payload.expires_at,
        details=payload.details or {},
    )
    session.add(consent)
    await session.flush()
    add_audit_event(
        session,
        action="safety.consent.create",
        entity_type="safety.consent",
        entity_id=consent.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "scope": consent.scope,
            "granted": consent.granted,
        },
    )
    await session.commit()
    await session.refresh(consent)
    return consent


@router.post(
    "/consents/{consent_id}/revoke",
    response_model=ConsentOut,
)
async def revoke_consent(
    consent_id: uuid.UUID,
    payload: ConsentRevoke,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(CONSENTS_MANAGE),
) -> Consent:
    consent = await session.get(Consent, consent_id)
    if consent is None or consent.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found",
        )
    # Resolve the school via the student record.
    student = await session.get(User, consent.student_id)
    if student is None or student.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent student not found",
        )
    school_id = student.school_id
    if school_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent school not found",
        )
    if (
        current_user.role != "superadmin"
        and school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke consent from another school",
        )
    if not consent.granted or consent.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent is already revoked",
        )

    consent.granted = False
    consent.revoked_at = _now()
    consent.details = {**consent.details, "revoked_reason": payload.reason}
    add_audit_event(
        session,
        action="safety.consent.revoke",
        entity_type="safety.consent",
        entity_id=consent.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "scope": consent.scope,
            "granted": consent.granted,
        },
    )
    await session.commit()
    await session.refresh(consent)
    return consent


@router.get("/geolocation", response_model=list[GeolocationPointOut])
async def list_geolocation(
    school_id: TenantSchoolId,
    session: SessionDep,
    student_id: uuid.UUID | None = Query(None, alias="student_id"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(GEO_READ),
) -> list[GeolocationPoint]:
    statement = select(GeolocationPoint).where(
        GeolocationPoint.deleted_at.is_(None),
    )
    if student_id is not None:
        student = await session.get(User, student_id)
        if (
            student is None
            or student.deleted_at is not None
            or student.role != "student"
            or student.school_id != school_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student not found in this school",
            )
        statement = statement.where(GeolocationPoint.student_id == student_id)
    else:
        statement = statement.join(
            User, User.id == GeolocationPoint.student_id
        ).where(User.school_id == school_id)
    statement = (
        statement.order_by(GeolocationPoint.recorded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post(
    "/geolocation",
    response_model=GeolocationPointOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_geolocation_point(
    payload: GeolocationPointCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(APPEALS_USE),
) -> GeolocationPoint:
    school_id = await _resolve_school_id(current_user, payload.school_id)
    safety_settings = await _load_safety_settings(session, school_id)
    if not safety_settings["geolocation_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Geolocation is disabled for this school",
        )
    await _assert_student_in_school(session, school_id, payload.student_id)
    await _assert_geolocation_requester_access(
        session, current_user, school_id, payload.student_id, current_user.id
    )
    # Geolocation requires an active consent (Law No. 99-З, Art. 5/8).
    consent = await _assert_active_geolocation_consent(session, payload.student_id)

    point = GeolocationPoint(
        student_id=payload.student_id,
        device_id=payload.device_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        event_type=payload.event_type,
        recorded_at=payload.recorded_at or _now(),
        consent_id=consent.id,
    )
    session.add(point)
    await session.flush()
    add_audit_event(
        session,
        action="safety.geolocation.create",
        entity_type="safety.geolocation_point",
        entity_id=point.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "event_type": point.event_type,
            "student_id": str(point.student_id),
        },
    )
    await session.commit()
    await session.refresh(point)
    return point


@router.get("/settings", response_model=SafetySettings)
async def get_safety_settings(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(None, alias="school_id"),
    _user: User = Depends(SETTINGS_READ),
) -> dict:
    """Return safety restrictions; superadmin may inspect any school."""
    target = _settings_scope(current_user, school_id)
    return await _load_safety_settings(session, target)


@router.put("/settings", response_model=SafetySettings)
async def update_safety_settings(
    payload: SafetySettingsUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(None, alias="school_id"),
    _user: User = Depends(SETTINGS_MANAGE),
) -> dict:
    """Update safety restrictions. Values below lawful defaults are rejected."""
    target = _settings_scope(current_user, school_id)
    current = await _load_safety_settings(session, target)
    updates = payload.model_dump(exclude_none=True)
    merged = {**current, **updates}

    if merged["incident_retention_days"] < merged["retention_days"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="incident_retention_days cannot be less than retention_days",
        )
    if merged["consent_age_threshold"] < 16:
        # Law No. 99-З, Art. 5(8): minors under 16 act through a legal
        # representative. The threshold may be raised but never lowered.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="consent_age_threshold cannot be less than 16",
        )

    key = SAFETY_SETTINGS_KEY if target is None else f"{SAFETY_SETTINGS_KEY}:{target}"
    setting = await session.get(Setting, key)
    if setting is None:
        setting = Setting(
            key=key,
            value=merged,
            description="Safety service restrictions (Law No. 99-З).",
        )
        session.add(setting)
    else:
        setting.value = merged
        setting.updated_by = str(current_user.id)
    add_audit_event(
        session,
        action="safety.settings.update",
        entity_type="safety.settings",
        entity_id=key,
        school_id=target,
        user_id=current_user.id,
        details={"updated": sorted(updates)},
    )
    await session.commit()
    return await _load_safety_settings(session, target)


@router.post("/maintenance/purge", response_model=SafetyPurgeResult)
async def purge_expired_data(
    current_user: CurrentUser,
    session: SessionDep,
    school_id: uuid.UUID | None = Query(None, alias="school_id"),
    _user: User = Depends(SETTINGS_MANAGE),
) -> SafetyPurgeResult:
    """Hard-delete records that exceeded the configured retention period.

    Law No. 99-З, Art. 4(8): storage is limited to the period required for the
    declared purposes. Superadmin may purge a single school or all schools;
    a school administrator may purge only their own school.
    """
    if current_user.role == "superadmin":
        target_school = school_id
    else:
        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School context is required",
            )
        target_school = current_user.school_id

    safety_settings = await _load_safety_settings(session, target_school)
    retention_days = int(safety_settings["retention_days"])
    incident_retention_days = int(safety_settings["incident_retention_days"])
    now = _now()
    cutoff = now - timedelta(days=retention_days)
    incident_cutoff = now - timedelta(days=incident_retention_days)

    appeal_stmt = delete(SupportAppeal).where(SupportAppeal.created_at < cutoff)
    incident_stmt = delete(Incident).where(Incident.created_at < incident_cutoff)
    consent_stmt = delete(Consent).where(Consent.created_at < cutoff)
    geo_stmt = delete(GeolocationPoint).where(GeolocationPoint.recorded_at < cutoff)

    if target_school is not None:
        appeal_stmt = appeal_stmt.where(SupportAppeal.school_id == target_school)
        incident_stmt = incident_stmt.where(Incident.school_id == target_school)
        student_ids = select(User.id).where(User.school_id == target_school)
        consent_stmt = consent_stmt.where(Consent.student_id.in_(student_ids))
        geo_stmt = geo_stmt.where(GeolocationPoint.student_id.in_(student_ids))

    deleted_appeals = (await session.execute(appeal_stmt)).rowcount or 0
    deleted_incidents = (await session.execute(incident_stmt)).rowcount or 0
    deleted_consents = (await session.execute(consent_stmt)).rowcount or 0
    deleted_geolocation = (await session.execute(geo_stmt)).rowcount or 0

    add_audit_event(
        session,
        action="safety.retention.purge",
        entity_type="safety.retention",
        entity_id=None,
        school_id=target_school,
        user_id=current_user.id,
        details={
            "deleted_appeals": deleted_appeals,
            "deleted_incidents": deleted_incidents,
            "deleted_consents": deleted_consents,
            "deleted_geolocation": deleted_geolocation,
            "retention_days": retention_days,
            "incident_retention_days": incident_retention_days,
        },
    )
    await session.commit()
    return SafetyPurgeResult(
        deleted_appeals=deleted_appeals,
        deleted_incidents=deleted_incidents,
        deleted_geolocation=deleted_geolocation,
        deleted_consents=deleted_consents,
        retention_days=retention_days,
        incident_retention_days=incident_retention_days,
        cutoff=cutoff,
        incident_cutoff=incident_cutoff,
    )
