"""Safety schemas: appeals, incidents, geolocation and consents."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SupportAppealCreate(BaseModel):
    school_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    category: Literal[
        "psychological", "conflict", "bullying", "family", "other"
    ] = "psychological"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=4000)
    is_anonymous: bool = False
    consent_required: bool = True
    consent_given: bool = False

    @field_validator("subject", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

    @model_validator(mode="after")
    def reject_anonymous_identity(self) -> "SupportAppealCreate":
        # Anonymous appeal must not carry an identity link.
        if self.is_anonymous and (self.student_id is not None or not self.consent_required):
            raise ValueError(
                "Anonymous appeal cannot specify a student or waive consent"
            )
        return self


class SupportAppealRespond(BaseModel):
    response: str = Field(min_length=1, max_length=4000)
    status: Literal["responded", "closed"] = "responded"

    @field_validator("response")
    @classmethod
    def strip_response(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Response cannot be blank")
        return value


class SupportAppealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID | None
    student_id: uuid.UUID | None
    requester_id: uuid.UUID | None
    category: str
    priority: str
    status: str
    subject: str
    message: str
    response: str | None
    responded_by_id: uuid.UUID | None
    responded_at: datetime | None
    closed_at: datetime | None
    is_anonymous: bool
    consent_required: bool
    consent_given: bool
    created_at: datetime
    updated_at: datetime


class IncidentCreate(BaseModel):
    school_id: uuid.UUID | None = None
    category: Literal[
        "bullying", "violence", "self_harm", "health", "facility", "other"
    ] = "other"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class IncidentResolve(BaseModel):
    actions_taken: str | None = Field(default=None, max_length=4000)
    status: Literal["resolved", "closed"] = "resolved"

    @field_validator("actions_taken")
    @classmethod
    def strip_actions(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    category: str
    severity: str
    title: str
    description: str | None
    reported_by_id: uuid.UUID | None
    status: str
    resolved_by_id: uuid.UUID | None
    resolved_at: datetime | None
    actions_taken: str | None
    created_at: datetime
    updated_at: datetime


class GeolocationPointCreate(BaseModel):
    school_id: uuid.UUID | None = None
    student_id: uuid.UUID
    device_id: str | None = Field(default=None, max_length=128)
    latitude: float
    longitude: float
    accuracy_m: float | None = Field(default=None, ge=0)
    event_type: Literal["location", "enter_school", "leave_school"] = "location"
    recorded_at: datetime | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class GeolocationPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    device_id: str | None
    latitude: float
    longitude: float
    accuracy_m: float | None
    event_type: str
    recorded_at: datetime
    consent_id: uuid.UUID | None


class ConsentCreate(BaseModel):
    school_id: uuid.UUID | None = None
    student_id: uuid.UUID
    legal_representative_id: uuid.UUID
    scope: Literal[
        "geolocation",
        "psychological_support",
        "incident_reporting",
        "health_data",
    ]
    granted: bool = True
    source: Literal["written", "electronic", "verbal_recorded"] = "electronic"
    expires_at: datetime | None = None
    details: dict | None = Field(default=None)


class ConsentRevoke(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    legal_representative_id: uuid.UUID
    scope: str
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None
    expires_at: datetime | None
    source: str
    details: dict
    created_at: datetime
    updated_at: datetime


class SafetySettings(BaseModel):
    """Administrator-adjustable safety restrictions with lawful defaults."""

    model_config = ConfigDict(from_attributes=True)

    retention_days: int = Field(default=365, ge=1, le=3650)
    incident_retention_days: int = Field(default=1095, ge=1, le=3650)
    consent_age_threshold: int = Field(default=16, ge=16, le=18)
    allow_anonymous_appeals: bool = True
    geolocation_enabled: bool = True


class SafetySettingsUpdate(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    incident_retention_days: int | None = Field(default=None, ge=1, le=3650)
    # Below 16 is rejected: Law No. 99-З, Art. 5(8).
    consent_age_threshold: int | None = Field(default=None, ge=16, le=18)
    allow_anonymous_appeals: bool | None = None
    geolocation_enabled: bool | None = None


class SafetyPurgeResult(BaseModel):
    deleted_appeals: int = 0
    deleted_incidents: int = 0
    deleted_geolocation: int = 0
    deleted_consents: int = 0
    retention_days: int
    incident_retention_days: int
    cutoff: datetime
    incident_cutoff: datetime
