"""Concrete readiness checks for the running platform."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.db.migration_state import read_migration_state
from app.db.session import get_engine, ping_database
from app.infra.redis_probe import ping_redis
from app.services.readiness import ReadinessCheck


class PendingMigrationsError(RuntimeError):
    pass


def build_checks(settings: Settings) -> list[ReadinessCheck]:
    async def database() -> str | None:
        await asyncio.to_thread(ping_database, get_engine())
        return None

    async def migrations() -> str | None:
        state = await asyncio.to_thread(read_migration_state, get_engine())
        if not state.up_to_date:
            raise PendingMigrationsError(f"db={state.current} code={state.heads}")
        return f"revision {', '.join(state.current) or 'none'}"

    async def redis() -> str | None:
        await ping_redis(settings.redis_url, timeout=settings.readiness_check_timeout_seconds)
        return None

    return [
        ReadinessCheck("database", database, required=True),
        ReadinessCheck(
            "migrations", migrations, required=True, failure_detail="pending or unreadable"
        ),
        ReadinessCheck("redis", redis, required=settings.redis_required),
    ]
