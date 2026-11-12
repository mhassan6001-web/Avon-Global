"""HTTP middleware: request id propagation, access logging, security headers.

Implemented as pure ASGI middleware (not ``BaseHTTPMiddleware``) so it does not
interfere with streaming responses or WebSockets added in later stages.
"""

from __future__ import annotations

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import REQUEST_ID_HEADER, resolve_request_id, set_request_id

access_logger = logging.getLogger("aven.access")

SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"camera=(), geolocation=(), microphone=(self)"),
    (b"cache-control", b"no-store"),
)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", []):
            if name == REQUEST_ID_HEADER.lower().encode():
                incoming = value.decode("latin-1")
                break
        request_id = resolve_request_id(incoming)
        set_request_id(request_id)

        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                if REQUEST_ID_HEADER.lower().encode() not in existing:
                    headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                for name, value in SECURITY_HEADERS:
                    if name not in existing:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            path = scope.get("path", "")
            level = logging.DEBUG if "/health/" in path else logging.INFO
            access_logger.log(
                level,
                "request completed",
                extra={
                    "method": scope.get("method"),
                    "path": path,
                    "status": status_holder["status"],
                    "duration_ms": duration_ms,
                },
            )
            # The request id is intentionally NOT cleared here: Starlette's
            # outermost ServerErrorMiddleware runs the 500 handler after this
            # middleware has unwound, and it still needs the id. Each request
            # runs in its own task/context, so the value cannot leak across
            # requests.
