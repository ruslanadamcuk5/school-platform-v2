"""Education level, programme and academic profile schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EducationLevel = Literal["primary", "secondary", "vocational", "higher"]
CurriculumStatus = Literal["draft", "approved", "archived"]
CurriculumComponentType = Literal[
    "discipline", "module", "practice", "coursework", "internship", "other"
]
AssessmentType = Literal[
    "exam",
    "credit",
    "differentiated_credit",
    "coursework",
    "practice_report",
    "other",
]
SessionStatus = Literal["planned", "active", "completed", "archived"]
SessionType = Literal["winter", "summer", "additional", "other"]
StatementStatus = Literal["draft", "published", "approved", "archived"]
StatementResult = Literal[
    "planned", "passed", "failed", "not_appeared", "exempt", "transferred"
]
CreditTransferStatus = Literal[
    "draft", "pending", "approved", "rejected", "archived"
]


class EducationLevelOut(BaseModel):
    code: EducationLevel
    name: str
    short_name: str
    icon: str
    description: str
    service_code: str
    read_permission: str
    manage_permission: str
    program_permission: str | None = None
    profile_read_permission: str | None = None
    profile_manage_permission: str | None = None
    is_professional: bool


class EducationGroupOut(BaseModel):
    id: uuid.UUID
    name: str
    grade: int
    letter: str
    education_level: EducationLevel
    course_year: int | None = None
    program_id: uuid.UUID | None = None
    program_name: str | None = None
    academic_year: str
    students: int = 0
    curator_name: str | None = None
    is_active: bool


class EducationTotalsOut(BaseModel):
    students: int = 0
    teachers: int = 0
    groups: int = 0
    programs: int = 0


class EducationProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: uuid.UUID
    code: str
    name: str
    education_level: EducationLevel
    qualification: str | None = None
    duration_years: int | None = None
    profile: dict = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EducationProgramCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    duration_years: int | None = Field(default=None, ge=1, le=10)
    profile: dict = Field(default_factory=dict)
    is_active: bool = True


class EducationProgramUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    duration_years: int | None = Field(default=None, ge=1, le=10)
    profile: dict | None = None
    is_active: bool | None = None


class CurriculumComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    curriculum_id: uuid.UUID
    code: str
    name: str
    component_type: CurriculumComponentType
    semester: int
    credits: float
    academic_hours: int
    contact_hours: int
    assessment_type: AssessmentType
    is_optional: bool
    order_index: int
    description: str | None = None
    details: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CurriculumComponentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    component_type: CurriculumComponentType = "discipline"
    semester: int = Field(default=1, ge=1, le=12)
    credits: float = Field(default=0, ge=0, le=100)
    academic_hours: int = Field(default=0, ge=0, le=20000)
    contact_hours: int = Field(default=0, ge=0, le=20000)
    assessment_type: AssessmentType = "exam"
    is_optional: bool = False
    order_index: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=1000)
    details: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contact_hours(self) -> "CurriculumComponentCreate":
        if self.contact_hours > self.academic_hours:
            raise ValueError(
                "contact_hours cannot exceed academic_hours"
            )
        return self


class CurriculumComponentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    component_type: CurriculumComponentType | None = None
    semester: int | None = Field(default=None, ge=1, le=12)
    credits: float | None = Field(default=None, ge=0, le=100)
    academic_hours: int | None = Field(default=None, ge=0, le=20000)
    contact_hours: int | None = Field(default=None, ge=0, le=20000)
    assessment_type: AssessmentType | None = None
    is_optional: bool | None = None
    order_index: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=1000)
    details: dict | None = None


class EducationCurriculumOut(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    program_id: uuid.UUID
    program_name: str
    education_level: EducationLevel
    academic_year: str
    name: str
    description: str | None = None
    status: CurriculumStatus
    approved_at: datetime | None = None
    approved_by_id: uuid.UUID | None = None
    profile: dict = Field(default_factory=dict)
    total_credits: float = 0
    components: list[CurriculumComponentOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EducationCurriculumCreate(BaseModel):
    program_id: uuid.UUID
    academic_year: str = Field(pattern=r"^\d{4}/\d{4}$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    status: CurriculumStatus = "draft"
    profile: dict = Field(default_factory=dict)


class EducationCurriculumUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    status: CurriculumStatus | None = None
    profile: dict | None = None


class StudentAcademicProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    login: str
    full_name: str
    institution_id: uuid.UUID
    program_id: uuid.UUID | None = None
    program_name: str | None = None
    group_id: uuid.UUID | None = None
    group_name: str | None = None
    course_year: int | None = None
    record_book_number: str | None = None
    funding_type: str
    enrollment_year: int | None = None
    academic_status: str
    profile: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StudentAcademicProfileCreate(BaseModel):
    user_id: uuid.UUID
    program_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    course_year: int | None = Field(default=None, ge=1, le=10)
    record_book_number: str | None = Field(default=None, max_length=64)
    funding_type: Literal["budget", "paid", "target", "other"] = "budget"
    enrollment_year: int | None = Field(default=None, ge=2000, le=2100)
    academic_status: Literal[
        "active", "academic_leave", "expelled", "graduated"
    ] = "active"
    profile: dict = Field(default_factory=dict)


class StudentAcademicProfileUpdate(BaseModel):
    program_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    course_year: int | None = Field(default=None, ge=1, le=10)
    record_book_number: str | None = Field(default=None, max_length=64)
    funding_type: Literal["budget", "paid", "target", "other"] | None = None
    enrollment_year: int | None = Field(default=None, ge=2000, le=2100)
    academic_status: Literal[
        "active", "academic_leave", "expelled", "graduated"
    ] | None = None
    profile: dict | None = None


class StaffAcademicProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    login: str
    full_name: str
    institution_id: uuid.UUID
    department: str | None = None
    position: str | None = None
    academic_degree: str | None = None
    academic_title: str | None = None
    profile: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StaffAcademicProfileCreate(BaseModel):
    user_id: uuid.UUID
    department: str | None = Field(default=None, max_length=255)
    position: str | None = Field(default=None, max_length=128)
    academic_degree: str | None = Field(default=None, max_length=128)
    academic_title: str | None = Field(default=None, max_length=128)
    profile: dict = Field(default_factory=dict)


class StaffAcademicProfileUpdate(BaseModel):
    department: str | None = Field(default=None, max_length=255)
    position: str | None = Field(default=None, max_length=128)
    academic_degree: str | None = Field(default=None, max_length=128)
    academic_title: str | None = Field(default=None, max_length=128)
    profile: dict | None = None


class EducationOverviewOut(BaseModel):
    institution_id: uuid.UUID
    institution_name: str
    institution_type: str
    institution_type_label: str
    education_levels: list[str] = Field(default_factory=list)
    level: EducationLevelOut
    academic_year: str
    available_years: list[str] = Field(default_factory=list)
    generated_at: datetime
    totals: EducationTotalsOut
    groups: list[EducationGroupOut] = Field(default_factory=list)
    programs: list[EducationProgramOut] = Field(default_factory=list)
    student_profiles_count: int = 0
    staff_profiles_count: int = 0


class AcademicSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: uuid.UUID
    education_level: EducationLevel
    academic_year: str
    semester: int
    name: str
    session_type: SessionType
    starts_on: date | None = None
    ends_on: date | None = None
    status: SessionStatus
    description: str | None = None
    profile: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AcademicSessionCreate(BaseModel):
    academic_year: str = Field(pattern=r"^\d{4}/\d{4}$")
    semester: int = Field(ge=1, le=12)
    name: str = Field(min_length=1, max_length=255)
    session_type: SessionType = "winter"
    starts_on: date | None = None
    ends_on: date | None = None
    status: SessionStatus = "planned"
    description: str | None = Field(default=None, max_length=1000)
    profile: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicSessionCreate":
        if (
            self.starts_on is not None
            and self.ends_on is not None
            and self.ends_on < self.starts_on
        ):
            raise ValueError("ends_on cannot be earlier than starts_on")
        return self


class AcademicSessionUpdate(BaseModel):
    academic_year: str | None = Field(
        default=None, pattern=r"^\d{4}/\d{4}$"
    )
    semester: int | None = Field(default=None, ge=1, le=12)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    session_type: SessionType | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    status: SessionStatus | None = None
    description: str | None = Field(default=None, max_length=1000)
    profile: dict | None = None


class StatementRecordOut(BaseModel):
    id: uuid.UUID
    statement_id: uuid.UUID
    student_id: uuid.UUID
    student_login: str
    student_name: str
    grade: int | None = None
    result: StatementResult
    credits_awarded: float = 0
    comment: str | None = None
    profile: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StatementRecordUpsert(BaseModel):
    student_id: uuid.UUID
    grade: int | None = Field(default=None, ge=1, le=10)
    result: StatementResult = "planned"
    credits_awarded: float | None = Field(default=None, ge=0, le=100)
    comment: str | None = None
    profile: dict = Field(default_factory=dict)


class StatementRecordBulk(BaseModel):
    records: list[StatementRecordUpsert] = Field(min_length=1, max_length=500)


class SessionStatementOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    institution_id: uuid.UUID
    education_level: EducationLevel
    group_id: uuid.UUID
    group_name: str
    curriculum_id: uuid.UUID
    curriculum_name: str
    component_id: uuid.UUID
    component_code: str
    component_name: str
    component_type: CurriculumComponentType
    semester: int
    component_credits: float
    teacher_id: uuid.UUID | None = None
    teacher_name: str | None = None
    statement_number: str
    issued_on: date
    status: StatementStatus
    approved_at: datetime | None = None
    approved_by_id: uuid.UUID | None = None
    notes: str | None = None
    profile: dict = Field(default_factory=dict)
    records: list[StatementRecordOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SessionStatementCreate(BaseModel):
    group_id: uuid.UUID
    component_id: uuid.UUID
    teacher_id: uuid.UUID | None = None
    statement_number: str = Field(min_length=1, max_length=64)
    issued_on: date | None = None
    notes: str | None = None
    profile: dict = Field(default_factory=dict)


class SessionStatementUpdate(BaseModel):
    teacher_id: uuid.UUID | None = None
    statement_number: str | None = Field(
        default=None, min_length=1, max_length=64
    )
    issued_on: date | None = None
    status: StatementStatus | None = None
    notes: str | None = None
    profile: dict | None = None


class CreditTransferOut(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    education_level: EducationLevel
    student_id: uuid.UUID
    student_login: str
    student_name: str
    target_program_id: uuid.UUID | None = None
    target_program_name: str | None = None
    target_component_id: uuid.UUID | None = None
    target_component_code: str | None = None
    target_component_name: str | None = None
    source_institution: str
    source_program: str
    source_component_code: str
    source_component_name: str
    source_academic_year: str
    source_credits: float
    awarded_credits: float
    source_grade: int | None = None
    document_number: str | None = None
    reason: str | None = None
    status: CreditTransferStatus
    decided_at: datetime | None = None
    decided_by_id: uuid.UUID | None = None
    profile: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreditTransferCreate(BaseModel):
    student_id: uuid.UUID
    target_program_id: uuid.UUID | None = None
    target_component_id: uuid.UUID | None = None
    source_institution: str = Field(min_length=1, max_length=255)
    source_program: str = Field(min_length=1, max_length=255)
    source_component_code: str = Field(min_length=1, max_length=64)
    source_component_name: str = Field(min_length=1, max_length=255)
    source_academic_year: str = Field(pattern=r"^\d{4}/\d{4}$")
    source_credits: float = Field(ge=0, le=100)
    awarded_credits: float | None = Field(default=None, ge=0, le=100)
    source_grade: int | None = Field(default=None, ge=1, le=10)
    document_number: str | None = Field(default=None, max_length=64)
    reason: str | None = None
    status: CreditTransferStatus = "draft"
    profile: dict = Field(default_factory=dict)


class CreditTransferUpdate(BaseModel):
    target_program_id: uuid.UUID | None = None
    target_component_id: uuid.UUID | None = None
    awarded_credits: float | None = Field(default=None, ge=0, le=100)
    source_grade: int | None = Field(default=None, ge=1, le=10)
    document_number: str | None = Field(default=None, max_length=64)
    reason: str | None = None
    status: CreditTransferStatus | None = None
    profile: dict | None = None


class TranscriptItemOut(BaseModel):
    component_id: uuid.UUID | None = None
    component_code: str
    component_name: str
    semester: int | None = None
    credits: float
    grade: int | None = None
    result: StatementResult | Literal["recognized"]
    source: Literal["statement", "transfer"]
    academic_year: str
    statement_id: uuid.UUID | None = None
    transfer_id: uuid.UUID | None = None
    statement_number: str | None = None
    document_number: str | None = None
    issued_on: date | None = None
    decided_at: datetime | None = None


class TranscriptOut(BaseModel):
    student_id: uuid.UUID
    login: str
    full_name: str
    record_book_number: str | None = None
    program_id: uuid.UUID | None = None
    program_name: str | None = None
    group_id: uuid.UUID | None = None
    group_name: str | None = None
    curriculum_id: uuid.UUID | None = None
    curriculum_name: str | None = None
    academic_year: str | None = None
    total_credits: float = 0
    curriculum_total_credits: float = 0
    progress_percent: int = 0
    items: list[TranscriptItemOut] = Field(default_factory=list)
    generated_at: datetime
