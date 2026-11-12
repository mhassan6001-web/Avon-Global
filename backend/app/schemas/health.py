"""Response schemas for the health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CheckStatus(StrEnum):
    OK = "ok"
    FAILING = "failing"
    SKIPPED = "skipped"


class LivenessResponse(BaseModel):
    status: CheckStatus = CheckStatus.OK
    service: str
    version: str
    environment: str
    timestamp: datetime


class DependencyCheck(BaseModel):
    name: str
    status: CheckStatus
    required: bool
    latency_ms: float | None = Field(default=None, ge=0)
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: CheckStatus
    service: str
    version: str
    environment: str
    timestamp: datetime
    checks: list[DependencyCheck]
