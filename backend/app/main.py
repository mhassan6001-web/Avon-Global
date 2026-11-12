"""AVEN GLOBAL API application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.request_context import REQUEST_ID_HEADER
from app.db.session import dispose_engine

logger = logging.getLogger("aven.app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format.value)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "starting",
            extra={"version": settings.app_version, "environment": settings.app_env.value},
        )
        yield
        dispose_engine()
        logger.info("stopped")

    docs_enabled = not settings.is_production
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_v1_prefix}/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Added last so it is the outermost middleware and every response carries a request id.
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app, settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


# Run with: uvicorn app.main:create_app --factory
