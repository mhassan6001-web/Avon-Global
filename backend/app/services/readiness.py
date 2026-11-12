"""Readiness evaluation.

Each dependency check is a named async callable. A check passes by returning
(optionally with a detail string) and fails by raising. Required failures make
the service not-ready; optional failures are reported but do not.

Failure details are deliberately generic in responses (no hostnames, no driver
messages); the full exception is logged server-side.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from app.schemas.health import CheckStatus, DependencyCheck

logger = logging.getLogger("aven.readiness")

CheckFn = Callable[[], Awaitable[str | None]]


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    run: CheckFn
    required: bool = True
    failure_detail: str = "unavailable"


async def _execute(check: ReadinessCheck, timeout: float) -> DependencyCheck:
    started = time.perf_counter()
    try:
        detail = await asyncio.wait_for(check.run(), timeout=timeout)
    except TimeoutError:
        logger.warning("readiness check timed out", extra={"check": check.name})
        return DependencyCheck(
            name=check.name,
            status=CheckStatus.FAILING,
            required=check.required,
            detail="timed out",
        )
    except Exception:
        logger.warning("readiness check failed", extra={"check": check.name}, exc_info=True)
        return DependencyCheck(
            name=check.name,
            status=CheckStatus.FAILING,
            required=check.required,
            detail=check.failure_detail,
        )
    return DependencyCheck(
        name=check.name,
        status=CheckStatus.OK,
        required=check.required,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        detail=detail,
    )


async def evaluate(
    checks: Sequence[ReadinessCheck], timeout: float
) -> tuple[CheckStatus, list[DependencyCheck]]:
    results = list(await asyncio.gather(*(_execute(c, timeout) for c in checks)))
    ready = all(r.status is CheckStatus.OK for r in results if r.required)
    return (CheckStatus.OK if ready else CheckStatus.FAILING), results
