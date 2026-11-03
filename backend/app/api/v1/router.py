"""Versioned API router."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analytics,
    assessment,
    auth,
    groups,
    journal,
    library,
    lms,
    me,
    onboarding,
    org,
    services,
    system,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(groups.router)
api_router.include_router(services.router)
api_router.include_router(org.router)
api_router.include_router(admin.router)
api_router.include_router(lms.router)
api_router.include_router(assessment.router)
api_router.include_router(journal.router)
api_router.include_router(library.router)
api_router.include_router(analytics.router)
api_router.include_router(onboarding.router)
