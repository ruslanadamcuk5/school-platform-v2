"""Standalone service application factory.

The pilot runs every domain in one gateway (``app.main:app``).  In production a
domain can be packaged and started on its own:

    SERVICE_CODE=library uvicorn app.service_app:create_service_app --factory

The factory keeps the same JWT, tenant, security-header and health contract as
the gateway, but mounts only the routers owned by the requested service.
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.v1 import (
    admin,
    assessment,
    auth,
    groups,
    journal,
    library,
    lms,
    me,
    org,
    services,
    system,
)
from app.api.v1.system import build_health
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.services.registry import SERVICE_BY_CODE

log = logging.getLogger("school-platform.service")

ROUTER_MAP = {
    "system": (system.router, services.router),
    "iam": (auth.router, groups.router, me.router),
    "org": (org.router,),
    "audit": (admin.router,),
    "admin": (admin.router,),
    "lms": (lms.router,),
    "assessment": (assessment.router,),
    "journal": (journal.router,),
    "library": (library.router,),
}


def _middleware(app: FastAPI) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_headers_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if settings.app_env != "production":
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


def create_service_app(service_code: str | None = None) -> FastAPI:
    """Build a FastAPI application for one service.

    ``service_code`` falls back to the ``SERVICE_CODE`` environment variable.
    Unknown or not-yet-implemented services still expose health and metadata,
    which keeps deployment pipelines uniform.
    """
    code = (service_code or os.getenv("SERVICE_CODE", "system")).strip().lower()
    manifest = SERVICE_BY_CODE.get(code)
    if manifest is None:
        raise RuntimeError(f"Unknown platform service: {code}")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            log.info("Service %s: database connection verified", code)
        except Exception as exc:  # health endpoint reports the detail
            log.warning("Service %s: database is not available: %s", code, exc)
        yield
        await engine.dispose()

    app = FastAPI(
        title=f"{settings.app_name} — {manifest.name}",
        description=manifest.description,
        version=manifest.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "Школьник", "url": settings.app_url},
        license_info={"name": "Proprietary"},
    )
    _middleware(app)

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> PlainTextResponse:
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    @app.get("/", tags=["system"], summary="Информация о сервисе")
    async def root():
        return {
            "service": code,
            "name": manifest.name,
            "version": manifest.version,
            "environment": settings.app_env,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }

    @app.get("/health", tags=["system"], summary="Проверка доступности")
    async def health():
        async with AsyncSessionLocal() as session:
            payload, status_code = await build_health(session)
        if status_code != 200:
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=status_code, content=payload)
        return payload

    routers = ROUTER_MAP.get(code, ())
    for router in routers:
        app.include_router(router, prefix="/api/v1")

    if not routers:
        @app.get(
            f"/api/v1/{code}/status",
            tags=["system"],
            summary="Состояние сервиса",
        )
        async def service_status():
            return {
                "service": code,
                "status": manifest.status,
                "version": manifest.version,
                "permissions": list(manifest.permission_codes),
            }

    return app


# Uvicorn can import ``app.service_app:app`` as well as the factory.
app = create_service_app(os.getenv("SERVICE_CODE", "system"))
