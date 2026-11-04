"""Contract tests for education levels and their service manifests."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.education import (
    DEFAULT_LEVELS_BY_INSTITUTION_TYPE,
    EDUCATION_LEVELS,
    LEVEL_INFO,
    LEVEL_SERVICE_CODES,
    level_for_grade,
    normalize_level,
)
from app.main import app
from app.schemas.education import (
    AcademicSessionCreate,
    CompetencyCreate,
    CompetencyMatrixBulk,
    CreditTransferCreate,
    CurriculumComponentCreate,
    EducationCurriculumCreate,
    PracticeContractCreate,
    PracticeDiaryEntryCreate,
    PracticePlaceCreate,
    PracticePlacementCreate,
    ProgramCompetencyItem,
    StatementRecordBulk,
)
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE


def test_all_levels_have_a_service() -> None:
    for level in EDUCATION_LEVELS:
        code = LEVEL_SERVICE_CODES[level]
        manifest = SERVICE_BY_CODE[code]
        assert manifest.category == "education"
        assert manifest.api_prefix.endswith(level)
        assert LEVEL_INFO[level].service_code == code


def test_school_levels_are_enabled_by_default() -> None:
    assert SERVICE_BY_CODE["primary_education"].default_enabled is True
    assert SERVICE_BY_CODE["secondary_education"].default_enabled is True
    assert SERVICE_BY_CODE["vocational_education"].default_enabled is False
    assert SERVICE_BY_CODE["higher_education"].default_enabled is False


def test_level_permissions_are_published_and_namespaced() -> None:
    for level in EDUCATION_LEVELS:
        info = LEVEL_INFO[level]
        codes = [
            info.read_permission,
            info.manage_permission,
            info.program_permission,
            info.profile_read_permission,
            info.profile_manage_permission,
        ]
        for code in codes:
            if code is None:
                continue
            assert code in PERMISSION_BY_CODE
            assert code.startswith(f"{info.service_code}.")


def test_institution_type_defaults_cover_levels() -> None:
    assert set(DEFAULT_LEVELS_BY_INSTITUTION_TYPE["school"]) == {
        "primary",
        "secondary",
    }
    assert DEFAULT_LEVELS_BY_INSTITUTION_TYPE["college"] == ("vocational",)
    assert DEFAULT_LEVELS_BY_INSTITUTION_TYPE["university"] == ("higher",)


def test_grade_mapping_and_normalization() -> None:
    assert level_for_grade(1) == "primary"
    assert level_for_grade(4) == "primary"
    assert level_for_grade(5) == "secondary"
    assert level_for_grade(11) == "secondary"
    assert normalize_level(" HIGHER ") == "higher"
    assert normalize_level("unknown") is None


def test_legacy_roles_receive_education_read_permissions() -> None:
    assert legacy_allows("admin", "vocational_education.programs.manage") is True
    assert legacy_allows("teacher", "higher_education.read") is True
    assert legacy_allows("student", "primary_education.read") is True
    assert legacy_allows("parent", "higher_education.read") is False
    assert legacy_allows("teacher", "higher_education.manage") is False


def test_curriculum_requires_academic_year_format() -> None:
    with pytest.raises(ValidationError):
        EducationCurriculumCreate(
            program_id=uuid.uuid4(),
            academic_year="2026-2027",
            name="Основная программа",
        )

    curriculum = EducationCurriculumCreate(
        program_id=uuid.uuid4(),
        academic_year="2026/2027",
        name="Основная программа",
    )
    assert curriculum.status == "draft"
    assert curriculum.academic_year == "2026/2027"


def test_curriculum_component_validates_hours_and_defaults() -> None:
    with pytest.raises(ValidationError):
        CurriculumComponentCreate(
            code="MATH-101",
            name="Математика",
            academic_hours=100,
            contact_hours=120,
        )

    component = CurriculumComponentCreate(
        code="PRACTICE-01",
        name="Производственная практика",
        component_type="practice",
        semester=4,
        credits=6,
        academic_hours=216,
        contact_hours=0,
        assessment_type="practice_report",
    )
    assert component.component_type == "practice"
    assert component.credits == 6
    assert component.is_optional is False


def test_academic_session_validates_dates_and_defaults() -> None:
    with pytest.raises(ValidationError):
        AcademicSessionCreate(
            academic_year="2025/2026",
            semester=1,
            name="Зимняя сессия",
            starts_on=date(2026, 1, 20),
            ends_on=date(2026, 1, 10),
        )

    item = AcademicSessionCreate(
        academic_year="2025/2026",
        semester=1,
        name="Зимняя сессия",
        starts_on=date(2026, 1, 10),
        ends_on=date(2026, 1, 20),
    )
    assert item.session_type == "winter"
    assert item.status == "planned"


def test_statement_records_default_to_planned() -> None:
    payload = StatementRecordBulk(
        records=[{"student_id": uuid.uuid4(), "grade": 9}]
    )
    assert payload.records[0].result == "planned"
    assert payload.records[0].credits_awarded is None


def test_credit_transfer_validates_source_and_credits() -> None:
    with pytest.raises(ValidationError):
        CreditTransferCreate(
            student_id=uuid.uuid4(),
            source_institution="Колледж №1",
            source_program="Программирование",
            source_component_code="MATH-101",
            source_component_name="Математика",
            source_academic_year="2025-2026",
            source_credits=5,
        )

    with pytest.raises(ValidationError):
        CreditTransferCreate(
            student_id=uuid.uuid4(),
            source_institution="Колледж №1",
            source_program="Программирование",
            source_component_code="MATH-101",
            source_component_name="Математика",
            source_academic_year="2025/2026",
            source_credits=105,
        )

    item = CreditTransferCreate(
        student_id=uuid.uuid4(),
        source_institution="Колледж №1",
        source_program="Программирование",
        source_component_code="MATH-101",
        source_component_name="Математика",
        source_academic_year="2025/2026",
        source_credits=5,
    )
    assert item.awarded_credits is None
    assert item.status == "draft"


def test_session_and_credit_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/education/vocational/sessions" in paths
    assert (
        "/api/v1/education/higher/sessions/{session_id}/statements" in paths
    )
    assert (
        "/api/v1/education/vocational/statements/{statement_id}/records/bulk"
        in paths
    )
    assert (
        "/api/v1/education/higher/students/{profile_id}/transcript" in paths
    )
    assert "/api/v1/education/vocational/credit-transfers" in paths
    assert "/api/v1/education/higher/credit-transfers/{transfer_id}" in paths
    assert "/api/v1/education/primary/sessions" not in paths
    assert "/api/v1/education/secondary/credit-transfers" not in paths


def test_competency_schemas_validate_defaults_and_ranges() -> None:
    competency = CompetencyCreate(
        code="ПК-01",
        name="Профессиональная коммуникация",
    )
    assert competency.competency_type == "professional"
    assert competency.is_active is True

    with pytest.raises(ValidationError):
        ProgramCompetencyItem(competency_id=uuid.uuid4(), target_level=6)
    with pytest.raises(ValidationError):
        ProgramCompetencyItem(competency_id=uuid.uuid4(), weight=101)

    matrix = CompetencyMatrixBulk(
        links=[
            {
                "component_id": uuid.uuid4(),
                "competency_id": uuid.uuid4(),
                "weight": 25,
            }
        ]
    )
    assert matrix.links[0].weight == 25


def test_competency_routes_are_professional_only_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/education/vocational/competencies" in paths
    assert "/api/v1/education/higher/competencies/{competency_id}" in paths
    assert (
        "/api/v1/education/vocational/programs/{program_id}/competencies"
        in paths
    )
    assert (
        "/api/v1/education/higher/curricula/{curriculum_id}/competency-matrix"
        in paths
    )
    assert "/api/v1/education/primary/competencies" not in paths
    assert "/api/v1/education/secondary/competencies" not in paths


def test_practice_schemas_validate_defaults_and_ranges() -> None:
    place = PracticePlaceCreate(code="PR-01", name="Синтетическое предприятие")
    assert place.is_active is True
    assert place.profile == {}

    with pytest.raises(ValidationError):
        PracticeContractCreate(
            practice_place_id=uuid.uuid4(),
            contract_number="Д-01/2026",
            academic_year="2026/2027",
            starts_on=date(2027, 5, 1),
            ends_on=date(2027, 4, 1),
        )
    with pytest.raises(ValidationError):
        PracticeContractCreate(
            practice_place_id=uuid.uuid4(),
            contract_number="Д-01/2026",
            academic_year="2026-2027",
            starts_on=date(2027, 4, 1),
            ends_on=date(2027, 5, 1),
        )

    contract = PracticeContractCreate(
        practice_place_id=uuid.uuid4(),
        contract_number="Д-01/2026",
        academic_year="2026/2027",
        starts_on=date(2027, 4, 1),
        ends_on=date(2027, 5, 1),
    )
    assert contract.status == "draft"

    with pytest.raises(ValidationError):
        PracticePlacementCreate(
            contract_id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            starts_on=date(2027, 5, 1),
            ends_on=date(2027, 4, 1),
        )
    with pytest.raises(ValidationError):
        PracticePlacementCreate(
            contract_id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            starts_on=date(2027, 4, 1),
            ends_on=date(2027, 5, 1),
            total_hours=2001,
        )

    placement = PracticePlacementCreate(
        contract_id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        starts_on=date(2027, 4, 1),
        ends_on=date(2027, 5, 1),
    )
    assert placement.status == "planned"
    assert placement.total_hours == 0

    with pytest.raises(ValidationError):
        PracticeDiaryEntryCreate(
            entry_date=date(2027, 4, 1),
            hours=25,
            activity="Синтетическая работа",
        )

    entry = PracticeDiaryEntryCreate(
        entry_date=date(2027, 4, 1),
        hours=6,
        activity="Синтетическая работа",
    )
    assert entry.status == "draft"


def test_practice_routes_are_professional_only_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/education/vocational/practice-places" in paths
    assert "/api/v1/education/higher/practice-contracts" in paths
    assert "/api/v1/education/vocational/practice-placements" in paths
    assert (
        "/api/v1/education/higher/practice-placements/{placement_id}/diary"
        in paths
    )
    assert (
        "/api/v1/education/vocational/practice-placements/{placement_id}/assessment"
        in paths
    )
    assert "/api/v1/education/vocational/practice-diary/{entry_id}" in paths
    assert "/api/v1/education/primary/practice-places" not in paths
    assert "/api/v1/education/secondary/practice-contracts" not in paths
