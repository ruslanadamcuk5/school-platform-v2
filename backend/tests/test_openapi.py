from __future__ import annotations

from app.main import app


def test_openapi_contains_pilot_endpoints() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/health" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/org/schools" in paths
    assert "/api/v1/admin/stats" in paths


def test_bearer_auth_is_declared() -> None:
    schema = app.openapi()
    schemes = schema["components"]["securitySchemes"]
    assert any(item.get("scheme") == "bearer" for item in schemes.values())
