"""Communication API: in-app notifications."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    require_permission,
    require_service,
)
from app.models.communication import Notification
from app.models.iam import User
from app.schemas.communication import NotificationCreate, NotificationOut
from app.services.audit import add_audit_event

router = APIRouter(
    prefix="/communication",
    tags=["communication"],
    dependencies=[Depends(require_service("communication"))],
)

NOTIFICATIONS_READ = require_permission("communication.notifications.read")
NOTIFICATIONS_MANAGE = require_permission("communication.notifications.manage")


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    current_user: CurrentUser,
    session: SessionDep,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(NOTIFICATIONS_READ),
) -> list[Notification]:
    statement = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    statement = (
        statement.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(NOTIFICATIONS_READ),
) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    if notification.read_at is None:
        notification.read_at = _now()
        notification.status = "read"
        await session.commit()
        await session.refresh(notification)
    return notification


@router.post(
    "/notifications",
    response_model=NotificationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    payload: NotificationCreate,
    current_user: CurrentUser,
    session: SessionDep,
    _user: User = Depends(NOTIFICATIONS_MANAGE),
) -> Notification:
    recipient = await session.get(User, payload.user_id)
    if recipient is None or recipient.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found",
        )
    if (
        current_user.role != "superadmin"
        and recipient.school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot notify a user from another school",
        )

    notification = Notification(
        user_id=recipient.id,
        channel=payload.channel,
        notification_type=payload.notification_type,
        title=payload.title,
        body=payload.body,
        payload=payload.payload,
        sent_at=_now(),
        status="sent",
    )
    session.add(notification)
    await session.flush()
    add_audit_event(
        session,
        action="communication.notification.send",
        entity_type="communication.notification",
        entity_id=notification.id,
        school_id=recipient.school_id,
        user_id=current_user.id,
        details={
            "recipient_id": str(recipient.id),
            "notification_type": payload.notification_type,
        },
    )
    await session.commit()
    await session.refresh(notification)
    return notification
