"""Application error types and the standard error envelope.

Every error response from the API has the same shape::

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}

This module is framework-independent; the FastAPI handlers that use it live in
``app.core.error_handlers``.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, client-presentable errors."""

    status_code: int = 400
    code: str = "bad_request"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "The request conflicts with the current state of the resource."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "A required service is temporarily unavailable."


HTTP_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def code_for_status(status_code: int) -> str:
    return HTTP_STATUS_CODES.get(status_code, "internal_error" if status_code >= 500 else "error")


def error_envelope(
    *, code: str, message: str, request_id: str | None, details: Any = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message, "request_id": request_id}
    if details is not None:
        body["details"] = details
    return {"error": body}


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce Pydantic validation errors to fields safe to return to clients.

    The raw ``input`` is dropped so submitted values (which may include
    passwords or banking details in later stages) are never echoed back.
    """
    return [
        {
            "loc": [str(part) for part in err.get("loc", ())],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in errors
    ]
