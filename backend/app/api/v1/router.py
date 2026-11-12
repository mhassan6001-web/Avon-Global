"""Version 1 API router. Each module's router is listed in ROUTERS."""

from fastapi import APIRouter

from app.ai.router import router as jarvis_router
from app.ai.voice_router import router as voice_router
from app.api.v1.endpoints import health
from app.modules.comms.router import router as comms_router
from app.modules.crm.router import router as crm_router
from app.modules.director.router import router as director_router
from app.modules.finance.router import router as finance_router
from app.modules.hr.router import router as hr_router
from app.modules.inventory.router import router as inventory_router
from app.modules.logistics.router import router as logistics_router
from app.modules.organisation.router import router as organisation_router
from app.modules.procurement.router import router as procurement_router
from app.modules.tenders.router import router as tenders_router
from app.platform.admin.router import router as admin_router
from app.platform.approvals.router import router as approvals_router
from app.platform.files.router import router as files_router
from app.platform.identity.router import router as auth_router
from app.platform.realtime import router as realtime_router

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
    finance_router,
    inventory_router,
    logistics_router,
    hr_router,
    comms_router,
    jarvis_router,
    voice_router,
    realtime_router,
    approvals_router,
)

api_router = APIRouter()
for _router in ROUTERS:
    api_router.include_router(_router)
