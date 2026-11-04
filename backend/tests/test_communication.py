"""Communication notification schema and contract checks."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.communication import NotificationCreate
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE


def test_notification_payload_is_trimmed() -> None:
    payload = NotificationCreate(
        user_id=uuid.uuid4(),
        title="  Проверка  ",
        body="  Текст уведомления  ",
        notification_type="  system  ",
    )
    assert payload.title == "Проверка"
    assert payload.body == "Текст уведомления"
    assert payload.notification_type == "system"
    assert payload.channel == "in_app"


def test_blank_notification_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(user_id=uuid.uuid4(), title="   ")


def test_empty_notification_body_becomes_null() -> None:
    payload = NotificationCreate(user_id=uuid.uuid4(), title="Тест", body="   ")
    assert payload.body is None


def test_notification_channel_is_limited_to_in_app() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(
            user_id=uuid.uuid4(),
            title="Тест",
            channel="email",  # type: ignore[arg-type]
        )


def test_communication_permissions_are_registered() -> None:
    assert "communication.notifications.read" in PERMISSION_BY_CODE
    assert "communication.notifications.manage" in PERMISSION_BY_CODE
    assert SERVICE_BY_CODE["communication"].api_prefix == "/api/v1/communication"


def test_notification_permissions_respect_legacy_roles() -> None:
    for role in (
        "methodologist",
        "teacher",
        "student",
        "parent",
        "psychologist",
        "secretary",
    ):
        assert legacy_allows(role, "communication.notifications.read") is True
    assert legacy_allows("student", "communication.notifications.manage") is False
    assert legacy_allows("admin", "communication.notifications.manage") is True


def test_notification_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/communication/notifications"]
    assert "post" in paths["/api/v1/communication/notifications"]
    assert "post" in paths[
        "/api/v1/communication/notifications/{notification_id}/read"
    ]
