"""Documents API: secretariat requests for certificates and references."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    TenantSchoolId,
    require_permission,
    require_service,
)
from app.models.documents import DocumentRequest
from app.models.iam import User, UserRelation
from app.models.org import School
from app.schemas.documents import (
    DocumentRequestCreate,
    DocumentRequestOut,
    DocumentRequestProcess,
)
from app.services.audit import add_audit_event

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_service("documents"))],
)

REQUESTS_CREATE = require_permission("documents.requests.create")
REQUESTS_PROCESS = require_permission("documents.requests.process")

RequestStatus = Literal[
    "submitted",
    "in_progress",
    "ready",
    "rejected",
    "cancelled",
]
OPEN_STATUSES = {"submitted", "in_progress"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _ensure_school(session: SessionDep, school_id: uuid.UUID) -> None:
    if await session.get(School, school_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found",
        )


async def _ensure_student_access(
    session: SessionDep,
    current_user: CurrentUser,
    school_id: uuid.UUID,
    student_id: uuid.UUID | None,
) -> None:
    if student_id is None:
        return
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
    if current_user.role == "student" and student.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot request a document for another student",
        )
    if current_user.role == "parent":
        relation = await session.scalar(
            select(UserRelation.id).where(
                UserRelation.parent_id == current_user.id,
                UserRelation.child_id == student.id,
            )
        )
        if relation is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student is not linked to this parent",
            )


@router.get("/requests/mine", response_model=list[DocumentRequestOut])
async def list_my_document_requests(
    current_user: CurrentUser,
    session: SessionDep,
    status_filter: RequestStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(REQUESTS_CREATE),
) -> list[DocumentRequest]:
    statement = select(DocumentRequest).where(
        DocumentRequest.requester_id == current_user.id
    )
    if status_filter is not None:
        statement = statement.where(DocumentRequest.status == status_filter)
    statement = (
        statement.order_by(DocumentRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.get("/requests", response_model=list[DocumentRequestOut])
async def list_school_document_requests(
    school_id: TenantSchoolId,
    session: SessionDep,
    status_filter: RequestStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(REQUESTS_PROCESS),
) -> list[DocumentRequest]:
    statement = select(DocumentRequest).where(
        DocumentRequest.school_id == school_id
    )
    if status_filter is not None:
        statement = statement.where(DocumentRequest.status == status_filter)
    statement = (
        statement.order_by(DocumentRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post(
    "/requests",
    response_model=DocumentRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_request(
    payload: DocumentRequestCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(REQUESTS_CREATE),
) -> DocumentRequest:
    if current_user.role == "superadmin":
        if payload.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="school_id is required for superadmin",
            )
        school_id = payload.school_id
    else:
        if current_user.school_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School context is required",
            )
        if (
            payload.school_id is not None
            and payload.school_id != current_user.school_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create a request for another school",
            )
        school_id = current_user.school_id

    await _ensure_school(session, school_id)
    await _ensure_student_access(session, current_user, school_id, payload.student_id)

    request = DocumentRequest(
        school_id=school_id,
        requester_id=current_user.id,
        student_id=payload.student_id,
        document_type=payload.document_type,
        title=payload.title,
        reason=payload.reason,
        status="submitted",
    )
    session.add(request)
    await session.flush()
    add_audit_event(
        session,
        action="documents.request.create",
        entity_type="documents.request",
        entity_id=request.id,
        school_id=school_id,
        user_id=current_user.id,
        details={
            "document_type": request.document_type,
            "student_id": str(request.student_id) if request.student_id else None,
        },
    )
    await session.commit()
    await session.refresh(request)
    return request


@router.post(
    "/requests/{request_id}/process",
    response_model=DocumentRequestOut,
)
async def process_document_request(
    request_id: uuid.UUID,
    payload: DocumentRequestProcess,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(REQUESTS_PROCESS),
) -> DocumentRequest:
    request = await session.get(DocumentRequest, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document request not found",
        )
    if (
        current_user.role != "superadmin"
        and request.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot process a request from another school",
        )
    if request.status not in OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document request is already closed",
        )

    request.status = payload.status
    request.comment = payload.comment
    request.document_number = payload.document_number
    request.processed_by_id = current_user.id
    request.processed_at = _now()
    add_audit_event(
        session,
        action="documents.request.process",
        entity_type="documents.request",
        entity_id=request.id,
        school_id=request.school_id,
        user_id=current_user.id,
        details={"status": request.status},
    )
    await session.commit()
    await session.refresh(request)
    return request


@router.post(
    "/requests/{request_id}/cancel",
    response_model=DocumentRequestOut,
)
async def cancel_document_request(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(REQUESTS_CREATE),
) -> DocumentRequest:
    request = await session.get(DocumentRequest, request_id)
    if request is None or request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document request not found",
        )
    if request.status not in OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document request is already closed",
        )

    request.status = "cancelled"
    add_audit_event(
        session,
        action="documents.request.cancel",
        entity_type="documents.request",
        entity_id=request.id,
        school_id=request.school_id,
        user_id=current_user.id,
        details={},
    )
    await session.commit()
    await session.refresh(request)
    return request
