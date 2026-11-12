"""Version 1 API router. Each module's router is listed in ROUTERS."""

from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.modules.crm.router import router as crm_router
from app.modules.director.router import router as director_router
from app.modules.organisation.router import router as organisation_router
from app.modules.procurement.router import router as procurement_router
from app.modules.tenders.router import router as tenders_router
from app.platform.admin.router import router as admin_router
from app.platform.approvals.router import router as approvals_router
from app.platform.files.router import router as files_router
from app.platform.identity.router import router as auth_router

# Single list of module routers; the route-coverage test checks every route in it.
ROUTERS: tuple[APIRouter, ...] = (
    health.router,
    auth_router,
    admin_router,
    organisation_router,
    files_router,
    director_router,
    crm_router,
    tenders_router,
    procurement_router,
    approvals_router,
)

api_router = APIRouter()
for _router in ROUTERS:
    api_router.include_router(_router)
