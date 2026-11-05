"""Safety service schema, permissions and OpenAPI contract checks.

Covers the legal defaults of the Law of the Republic of Belarus No. 99-З of
07.05.2021 (as amended): consent for special personal data, anonymity without
identity links, consent revocation, and geolocation guarded by active consent.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.safety import (
    ConsentCreate,
    ConsentRevoke,
    GeolocationPointCreate,
    IncidentCreate,
    IncidentResolve,
    SafetySettings,
    SafetySettingsUpdate,
    SupportAppealCreate,
    SupportAppealRespond,
)
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE

SCHOOL_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()


def test_safety_service_manifest() -> None:
    service = SERVICE_BY_CODE["safety"]
    assert service.api_prefix == "/api/v1/safety"
    assert service.default_enabled is False


def test_safety_permissions_registered() -> None:
    for code in (
        "safety.support.use",
        "safety.incidents.read",
        "safety.incidents.manage",
        "safety.geolocation.read",
        "safety.consents.manage",
        "safety.settings.manage",
    ):
        assert code in PERMISSION_BY_CODE


def test_safety_legacy_role_mapping() -> None:
    assert legacy_allows("student", "safety.support.use") is True
    assert legacy_allows("parent", "safety.support.use") is True
    assert legacy_allows("psychologist", "safety.incidents.manage") is True
    assert legacy_allows("secretary", "safety.incidents.read") is True
    assert legacy_allows("secretary", "safety.consents.manage") is False
    assert legacy_allows("teacher", "safety.incidents.read") is True
    assert legacy_allows("teacher", "safety.incidents.manage") is False
    assert legacy_allows("admin", "safety.consents.manage") is True
    assert legacy_allows("student", "safety.incidents.manage") is False


def test_appeal_payload_is_trimmed() -> None:
    payload = SupportAppealCreate(
        school_id=SCHOOL_ID,
        student_id=STUDENT_ID,
        subject="  Тревога перед экзаменом  ",
        message="  Не могу спать  ",
        consent_given=True,
    )
    assert payload.subject == "Тревога перед экзаменом"
    assert payload.message == "Не могу спать"


def test_appeal_blank_subject_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SupportAppealCreate(subject="   ", message="Текст", consent_given=True)


def test_appeal_requires_consent_by_default() -> None:
    payload = SupportAppealCreate(subject="Тема", message="Текст")
    assert payload.consent_required is True
    assert payload.consent_given is False


def test_anonymous_appeal_cannot_carry_identity() -> None:
    with pytest.raises(ValidationError):
        SupportAppealCreate(
            student_id=STUDENT_ID,
            subject="Тема",
            message="Текст",
            is_anonymous=True,
            consent_given=True,
        )


def test_anonymous_appeal_cannot_waive_consent() -> None:
    with pytest.raises(ValidationError):
        SupportAppealCreate(
            subject="Тема",
            message="Текст",
            is_anonymous=True,
            consent_required=False,
            consent_given=True,
        )


def test_anonymous_appeal_is_valid_without_identity() -> None:
    payload = SupportAppealCreate(
        subject="Тема",
        message="Текст",
        is_anonymous=True,
        consent_given=True,
    )
    assert payload.student_id is None
    assert payload.is_anonymous is True


def test_appeal_response_is_trimmed() -> None:
    payload = SupportAppealRespond(response="  Мы рядом  ", status="responded")
    assert payload.response == "Мы рядом"


def test_incident_payload_is_trimmed() -> None:
    payload = IncidentCreate(
        school_id=SCHOOL_ID,
        title="  Конфликт в столовой  ",
        description="  Разговор с участниками  ",
        severity="high",
    )
    assert payload.title == "Конфликт в столовой"
    assert payload.description == "Разговор с участниками"


def test_incident_blank_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate(title="   ")


def test_incident_resolve_strips_actions() -> None:
    payload = IncidentResolve(actions_taken="  Проведена беседа  ")
    assert payload.actions_taken == "Проведена беседа"


def test_geolocation_rejects_out_of_range_coordinates() -> None:
    with pytest.raises(ValidationError):
        GeolocationPointCreate(student_id=STUDENT_ID, latitude=91, longitude=27)
    with pytest.raises(ValidationError):
        GeolocationPointCreate(student_id=STUDENT_ID, latitude=53, longitude=181)


def test_geolocation_accepts_valid_coordinates() -> None:
    payload = GeolocationPointCreate(
        student_id=STUDENT_ID, latitude=53.9, longitude=27.56, accuracy_m=15
    )
    assert payload.latitude == 53.9
    assert payload.longitude == 27.56


def test_consent_scope_is_validated() -> None:
    with pytest.raises(ValidationError):
        ConsentCreate(
            student_id=STUDENT_ID,
            legal_representative_id=uuid.uuid4(),
            scope="unknown_scope",  # type: ignore[arg-type]
        )


def test_consent_revoke_reason_is_trimmed() -> None:
    payload = ConsentRevoke(reason="  Передумал  ")
    assert payload.reason == "Передумал"


def test_consent_revoke_blank_reason_becomes_none() -> None:
    payload = ConsentRevoke(reason="   ")
    assert payload.reason is None


def test_consent_expiry_is_timezone_aware() -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    payload = ConsentCreate(
        student_id=STUDENT_ID,
        legal_representative_id=uuid.uuid4(),
        scope="geolocation",
        expires_at=expires,
    )
    assert payload.expires_at == expires


def test_safety_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/safety/appeals/mine"]
    assert "get" in paths["/api/v1/safety/appeals"]
    assert "post" in paths["/api/v1/safety/appeals"]
    assert "post" in paths["/api/v1/safety/appeals/{appeal_id}/respond"]
    assert "post" in paths["/api/v1/safety/appeals/{appeal_id}/close"]
    assert "get" in paths["/api/v1/safety/incidents"]
    assert "post" in paths["/api/v1/safety/incidents"]
    assert "post" in paths["/api/v1/safety/incidents/{incident_id}/resolve"]
    assert "get" in paths["/api/v1/safety/consents"]
    assert "post" in paths["/api/v1/safety/consents"]
    assert "post" in paths["/api/v1/safety/consents/{consent_id}/revoke"]
    assert "get" in paths["/api/v1/safety/geolocation"]
    assert "post" in paths["/api/v1/safety/geolocation"]
    assert "get" in paths["/api/v1/safety/settings"]
    assert "put" in paths["/api/v1/safety/settings"]
    assert "post" in paths["/api/v1/safety/maintenance/purge"]


def test_safety_settings_defaults_follow_law() -> None:
    settings = SafetySettings()
    assert settings.consent_age_threshold == 16
    assert settings.retention_days == 365
    assert settings.incident_retention_days >= settings.retention_days
    assert settings.allow_anonymous_appeals is True
    assert settings.geolocation_enabled is True


def test_safety_settings_reject_lowered_consent_age() -> None:
    with pytest.raises(ValidationError):
        SafetySettingsUpdate(consent_age_threshold=15)


def test_safety_settings_accept_raised_consent_age() -> None:
    payload = SafetySettingsUpdate(consent_age_threshold=17)
    assert payload.consent_age_threshold == 17

