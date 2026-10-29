"""FastAPI application entry point for the «Школьник» platform."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.api.v1.system import build_health
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("school-platform")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        log.info("Database connection verified")
    except Exception as exc:  # health endpoint reports the detail
        log.warning("Database is not available at startup: %s", exc)
    yield
    await engine.dispose()
    log.info("Database engine disposed")


app = FastAPI(
    title=f"{settings.app_name} API",
    description=(
        "Единая образовательная онлайн-платформа «Школьник». "
        "Пилотный backend: JWT, RBAC и мультитенантность по school_id."
    ),
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={"name": "Школьник", "url": settings.app_url},
    license_info={"name": "Proprietary"},
    openapi_tags=[
        {"name": "system", "description": "Здоровье сервиса и метаданные"},
        {"name": "auth", "description": "Аутентификация и сессии"},
        {"name": "org", "description": "Школы, классы, мультитенантность"},
        {"name": "admin", "description": "Администрирование школы"},
        {"name": "lms", "description": "Предметы, темы, учебники и курсы"},
        {"name": "assessment", "description": "Тесты, работы, сдача и результаты"},
    ],
)

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
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.app_env != "production":
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if settings.app_env in {"pilot", "production"}:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


@app.get("/robots.txt", include_in_schema=False)
async def robots() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get("/", tags=["system"], summary="Информация о сервисе")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "api": "/api/v1",
    }


@app.get("/health", summary="Проверка доступности")
async def root_health():
    async with AsyncSessionLocal() as session:
        payload, status_code = await build_health(session)
    if status_code != 200:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=status_code, content=payload)
    return payload


app.include_router(api_router, prefix="/api/v1")
