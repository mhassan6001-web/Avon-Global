"""Health (liveness) and readiness endpoints.

* ``GET /api/v1/health/live``  — the process is up. No dependency calls; used by
  container orchestrators to decide whether to restart the process.
* ``GET /api/v1/health/ready`` — the service can handle traffic: database
  reachable, schema at the latest migration, Redis reachable. Returns 503 when
  a required dependency fails; used by load balancers.

Neither endpoint requires authentication, and neither reveals hostnames,
credentials or driver error messages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.platform.authz.deps import public
from app.schemas.health import CheckStatus, LivenessResponse, ReadinessResponse
from app.services.dependency_checks import build_checks
from app.services.readiness import ReadinessCheck, evaluate

router = APIRouter(prefix="/health", tags=["health"], dependencies=[Depends(public)])

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_readiness_checks(settings: SettingsDep) -> list[ReadinessCheck]:
    return build_checks(settings)


@router.get("/live", response_model=LivenessResponse, summary="Liveness probe")
async def live(settings: SettingsDep) -> LivenessResponse:
    return LivenessResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={503: {"model": ReadinessResponse, "description": "A required dependency failed"}},
)
async def ready(
    response: Response,
    settings: SettingsDep,
    checks: Annotated[list[ReadinessCheck], Depends(get_readiness_checks)],
) -> ReadinessResponse:
    overall, results = await evaluate(checks, timeout=settings.readiness_check_timeout_seconds)
    if overall is not CheckStatus.OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status=overall,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
        timestamp=datetime.now(UTC),
        checks=results,
    )
