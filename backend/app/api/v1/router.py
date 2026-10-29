"""Versioned API router."""
from fastapi import APIRouter

from app.api.v1 import admin, auth, lms, org, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(org.router)
api_router.include_router(admin.router)
api_router.include_router(lms.router)
