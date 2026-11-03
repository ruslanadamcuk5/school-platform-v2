from __future__ import annotations

from app.main import app


def test_openapi_contains_pilot_endpoints() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/health" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/org/regions" in paths
    assert "/api/v1/org/cities" in paths
    assert "/api/v1/org/schools" in paths
    assert "/api/v1/admin/stats" in paths
    assert "/api/v1/me/permissions" in paths
    assert "/api/v1/me/services" in paths
    assert "/api/v1/groups" in paths
    assert "/api/v1/services" in paths
    assert "/api/v1/analytics/overview" in paths
    assert "/api/v1/analytics/export.csv" in paths
    assert "/api/v1/education/primary/overview" in paths
    assert "/api/v1/education/secondary/overview" in paths
    assert "/api/v1/education/vocational/overview" in paths
    assert "/api/v1/education/higher/overview" in paths
    assert "/api/v1/education/vocational/curricula" in paths
    assert "/api/v1/education/higher/curricula" in paths
    assert (
        "/api/v1/education/vocational/curricula/{curriculum_id}" in paths
    )
    assert (
        "/api/v1/education/vocational/curricula/{curriculum_id}/components"
        in paths
    )


def test_bearer_auth_is_declared() -> None:
    schema = app.openapi()
    schemes = schema["components"]["securitySchemes"]
    assert any(item.get("scheme") == "bearer" for item in schemes.values())
