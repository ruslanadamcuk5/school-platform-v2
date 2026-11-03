"""Schemas for the personalised onboarding service."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingStepOut(BaseModel):
    code: str
    title: str
    body: str
    target: str | None = None
    route: str | None = None
    tip: str | None = None
    action: str = "next"
    duration_seconds: int = 30
    completed: bool = False


class OnboardingModuleOut(BaseModel):
    code: str
    service_code: str
    service_name: str
    service_icon: str
    stage: str
    title: str
    description: str
    icon: str
    estimated_minutes: int
    roles: list[str] | None = None
    is_addon: bool = False
    status: str = "not_started"
    current_step_code: str | None = None
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_activity_at: datetime | None = None
    steps: list[OnboardingStepOut] = Field(default_factory=list)


class OnboardingStageOut(BaseModel):
    code: str
    title: str
    description: str
    modules: list[OnboardingModuleOut] = Field(default_factory=list)
    total: int = 0
    completed: int = 0
    progress_percent: int = 0


class OnboardingOverviewOut(BaseModel):
    user_id: uuid.UUID
    role: str
    catalog_version: str
    generated_at: datetime
    known_service_codes: list[str] = Field(default_factory=list)
    stages: list[OnboardingStageOut] = Field(default_factory=list)
    modules: list[OnboardingModuleOut] = Field(default_factory=list)
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    not_started: int = 0
    addon_total: int = 0
    progress_percent: int = 0


class OnboardingProgressOut(BaseModel):
    module_code: str
    status: str
    current_step_code: str | None = None
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_activity_at: datetime | None = None


class OnboardingReportSummaryOut(BaseModel):
    total_users: int = 0
    users_not_started: int = 0
    users_in_progress: int = 0
    users_completed: int = 0
    modules_total: int = 0
    modules_completed: int = 0
    modules_in_progress: int = 0
    addon_modules: int = 0
    progress_percent: int = 0
    by_role: dict[str, int] = Field(default_factory=dict)


class OnboardingReportUserOut(BaseModel):
    user_id: uuid.UUID
    login: str
    full_name: str
    role: str
    school_id: uuid.UUID | None = None
    school_name: str | None = None
    modules_total: int = 0
    modules_completed: int = 0
    modules_in_progress: int = 0
    addon_modules: int = 0
    status: str = "not_started"
    progress_percent: int = 0
    last_activity_at: datetime | None = None


class OnboardingReportUsersOut(BaseModel):
    items: list[OnboardingReportUserOut] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    summary: OnboardingReportSummaryOut
