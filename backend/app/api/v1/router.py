"""Version 1 API router. Each module registers its router here."""

from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.modules.organisation.router import router as organisation_router
from app.platform.admin.router import router as admin_router
from app.platform.files.router import router as files_router
from app.platform.identity.router import router as auth_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(organisation_router)
api_router.include_router(files_router)
