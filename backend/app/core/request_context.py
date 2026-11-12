"""Per-request context (currently the request id) shared with logging."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_VALID_INCOMING_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def resolve_request_id(incoming: str | None) -> str:
    """Accept a well-formed id from a trusted proxy, otherwise generate one.

    Incoming values are restricted to a safe character set so they cannot be
    used to inject content into logs.
    """
    if incoming and _VALID_INCOMING_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex
