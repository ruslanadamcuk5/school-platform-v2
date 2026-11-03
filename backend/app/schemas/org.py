"""Organisation schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EducationLevel = Literal["primary", "secondary", "vocational", "higher"]
InstitutionType = Literal["school", "college", "university"]


class SchoolCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=120)
    institution_type: InstitutionType = "school"
    education_levels: list[EducationLevel] = Field(
        default_factory=lambda: ["primary", "secondary"],
        min_length=1,
    )
    city_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    director: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = None
    profile: dict = Field(default_factory=dict)
    is_active: bool = True


class SchoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=120)
    institution_type: InstitutionType | None = None
    education_levels: list[EducationLevel] | None = Field(default=None, min_length=1)
    city_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    director: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = None
    profile: dict | None = None
    is_active: bool | None = None


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    institution_type: str
    education_levels: list[str]
    profile: dict
    city: str | None
    address: str | None
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    created_at: datetime


class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    region_id: uuid.UUID
    code: str
    name: str
    city_type: str
    created_at: datetime


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    grade: int
    letter: str
    education_level: str
    program_id: uuid.UUID | None
    course_year: int | None
    profile: dict
    title: str | None
    academic_year: str
    homeroom_teacher_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    display_name: str
