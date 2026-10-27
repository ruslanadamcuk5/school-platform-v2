"""System endpoints: health, readiness and metadata."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import private_key_exists
from app.db.session import get_session
from app.schemas.common import HealthOut

router = APIRouter(tags=["system"])


async def build_health(session: AsyncSession) -> tuple[dict, int]:
    database = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        database = "error"

    payload = {
        "status": "ok" if database == "ok" else "degraded",
        "service": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "database": database,
        "jwt_ready": private_key_exists(),
        "time": datetime.now(timezone.utc).isoformat(),
    }
    return payload, 200 if database == "ok" else 503


@router.get("/health", response_model=HealthOut, summary="Проверка доступности")
async def health(session: AsyncSession = Depends(get_session)):
    payload, status_code = await build_health(session)
    if status_code != 200:
        return JSONResponse(status_code=status_code, content=payload)
    return payload


@router.get("/meta", summary="Метаданные приложения")
async def meta():
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "environment": settings.app_env,
        "languages": ["ru", "be", "en"],
        "features": {
            "jwt_auth": True,
            "rbac": True,
            "multi_tenancy": True,
            "openapi": True,
        },
    }
