"""Documents request schema, permissions and OpenAPI contract checks."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.documents import DocumentRequestCreate, DocumentRequestProcess
from app.services.access import legacy_allows
from app.services.registry import PERMISSION_BY_CODE, SERVICE_BY_CODE


def test_document_request_payload_is_trimmed() -> None:
    payload = DocumentRequestCreate(
        document_type="  certificate  ",
        title="  Справка об обучении  ",
        reason="  Для банка  ",
    )
    assert payload.document_type == "certificate"
    assert payload.title == "Справка об обучении"
    assert payload.reason == "Для банка"


def test_document_request_blank_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentRequestCreate(document_type="certificate", title="   ")


def test_ready_request_requires_document_number() -> None:
    with pytest.raises(ValidationError):
        DocumentRequestProcess(status="ready")


def test_document_number_is_only_allowed_for_ready_request() -> None:
    with pytest.raises(ValidationError):
        DocumentRequestProcess(status="rejected", document_number="123")


def test_document_number_is_trimmed() -> None:
    payload = DocumentRequestProcess(
        status="ready",
        document_number="  ШК-123/2026  ",
        comment="  Готово  ",
    )
    assert payload.document_number == "ШК-123/2026"
    assert payload.comment == "Готово"


def test_documents_permissions_and_legacy_roles() -> None:
    assert "documents.requests.create" in PERMISSION_BY_CODE
    assert "documents.requests.process" in PERMISSION_BY_CODE
    assert SERVICE_BY_CODE["documents"].api_prefix == "/api/v1/documents"
    assert legacy_allows("student", "documents.requests.create") is True
    assert legacy_allows("parent", "documents.requests.create") is True
    assert legacy_allows("teacher", "documents.requests.create") is False
    assert legacy_allows("secretary", "documents.requests.process") is True
    assert legacy_allows("admin", "documents.requests.process") is True
    assert legacy_allows("student", "documents.requests.process") is False


def test_document_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/documents/requests"]
    assert "get" in paths["/api/v1/documents/requests/mine"]
    assert "post" in paths["/api/v1/documents/requests"]
    assert "post" in paths[
        "/api/v1/documents/requests/{request_id}/process"
    ]
    assert "post" in paths[
        "/api/v1/documents/requests/{request_id}/cancel"
    ]
