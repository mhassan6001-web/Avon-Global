import json
import logging

import pytest

from app.core.logging import (
    REDACTED,
    ConsoleFormatter,
    JsonFormatter,
    RequestContextFilter,
    configure_logging,
)
from app.core.request_context import resolve_request_id, set_request_id


def _record(msg: str = "hello", **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("aven.test", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_structured_line() -> None:
    record = _record(path="/api/v1/health/live", status=200)
    RequestContextFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["path"] == "/api/v1/health/live"
    assert payload["status"] == 200
    assert payload["timestamp"].endswith("+00:00")


def test_sensitive_fields_are_redacted() -> None:
    record = _record(password="hunter2", api_key="abc", nested={"Authorization": "Bearer x"})
    payload = json.loads(JsonFormatter().format(record))
    assert payload["password"] == REDACTED
    assert payload["api_key"] == REDACTED
    assert payload["nested"]["Authorization"] == REDACTED


def test_request_id_attached_from_context() -> None:
    set_request_id("req-12345678")
    try:
        record = _record()
        RequestContextFilter().filter(record)
        assert "[req-12345678]" in ConsoleFormatter().format(record)
    finally:
        set_request_id(None)


def test_exception_included() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "aven.test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO", "json")
    configure_logging("INFO", "json")
    assert len(logging.getLogger().handlers) == 1
    assert logging.getLogger("uvicorn.access").disabled


@pytest.mark.parametrize("incoming", ["abcdefgh-1234", "A" * 64])
def test_well_formed_request_id_is_kept(incoming: str) -> None:
    assert resolve_request_id(incoming) == incoming


BAD_IDS = [None, "", "short", "has space here", "x" * 65, "a\nb-injected"]


@pytest.mark.parametrize("incoming", BAD_IDS)
def test_malformed_request_id_is_replaced(incoming: str | None) -> None:
    result = resolve_request_id(incoming)
    assert result != incoming
    assert len(result) == 32
