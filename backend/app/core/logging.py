"""Structured logging.

* ``json`` format (staging/production): one JSON object per line, ready for a
  log collector.
* ``console`` format (development): readable single-line output.

Every record carries the current request id (if any) so a request can be traced
across log lines. Values under keys that look like secrets are redacted.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id

_RESERVED = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}
_SENSITIVE_MARKERS = ("password", "secret", "token", "authorization", "api_key", "apikey", "cookie")
REDACTED = "[REDACTED]"


def _redact(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return REDACTED
    if isinstance(value, dict):
        return {k: _redact(str(k), v) for k, v in value.items()}
    return value


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: _redact(key, value)
        for key, value in vars(record).items()
        if key not in _RESERVED and not key.startswith("_")
    }


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        extras = _extra_fields(record)
        request_id = extras.pop("request_id", None)
        context = " ".join(f"{k}={v}" for k, v in extras.items())
        line = f"{timestamp} {record.levelname:<8} {record.name}"
        if request_id:
            line += f" [{request_id}]"
        line += f" {record.getMessage()}"
        if context:
            line += f" | {context}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    """Configure the root logger. Safe to call more than once."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if fmt == "json" else ConsoleFormatter())
    handler.addFilter(RequestContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Route server logs through our handler; the access log is replaced by our middleware.
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("sqlalchemy.engine").setLevel("WARNING")
