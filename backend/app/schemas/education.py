"""Education level, programme and academic profile schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
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
