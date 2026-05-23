"""
RAIYA API v1 Router — Aggregates all route modules.
"""

from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.jd import router as jd_router
from app.api.v1.routes.batch import router as batch_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.email import router as email_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(jd_router)
api_router.include_router(batch_router)
api_router.include_router(admin_router)
api_router.include_router(email_router)
