"""Tests for the standalone microservice application factory."""
from __future__ import annotations

import pytest

from app.service_app import create_service_app
from app.services.registry import SERVICES


def test_standalone_library_app_mounts_only_library_routes() -> None:
    app = create_service_app("library")
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/" in paths
    assert any(path.startswith("/api/v1/library") for path in paths)
    assert not any(path.startswith("/api/v1/journal") for path in paths)


def test_standalone_system_app_mounts_service_catalog() -> None:
    app = create_service_app("system")
    paths = app.openapi()["paths"]
    assert "/api/v1/services" in paths
    assert "/api/v1/health" in paths


def test_unknown_service_is_rejected() -> None:
    with pytest.raises(RuntimeError):
        create_service_app("unknown-service")


def test_every_registered_manifest_can_be_started() -> None:
    for manifest in SERVICES:
        app = create_service_app(manifest.code)
        schema = app.openapi()
        assert schema["info"]["version"] == manifest.version
