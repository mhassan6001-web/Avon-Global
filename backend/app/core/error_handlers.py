"""FastAPI exception handlers that emit the standard error envelope."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings
from app.core.errors import AppError, code_for_status, error_envelope, sanitize_validation_errors
from app.core.request_context import REQUEST_ID_HEADER, get_request_id

logger = logging.getLogger("aven.errors")


def _response(status_code: int, body: dict[str, object]) -> JSONResponse:
    request_id = get_request_id()
    headers = {REQUEST_ID_HEADER: request_id} if request_id else None
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_error_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("application error", extra={"code": exc.code})
        return _response(
            exc.status_code,
            error_envelope(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(
            422,
            error_envelope(
                code="validation_error",
                message="The request contains invalid data.",
                details=sanitize_validation_errors(list(exc.errors())),
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _response(
            exc.status_code,
            error_envelope(
                code=code_for_status(exc.status_code),
                message=message,
                request_id=get_request_id(),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled exception", extra={"path": request.url.path, "method": request.method}
        )
        details = (
            {"exception": type(exc).__name__, "detail": str(exc)}
            if settings.expose_error_details
            else None
        )
        return _response(
            500,
            error_envelope(
                code="internal_error",
                message="An unexpected error occurred. It has been logged.",
                details=details,
                request_id=get_request_id(),
            ),
        )
