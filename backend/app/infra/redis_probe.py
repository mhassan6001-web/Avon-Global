"""Minimal, dependency-free Redis health probe.

Stage 1 only needs to know whether Redis is reachable, so this sends a single
RESP ``PING`` (with ``AUTH``/``SELECT`` when the URL contains them) over a TCP
connection. The full ``redis`` client arrives with Celery background jobs.
"""

from __future__ import annotations

import asyncio
import contextlib
import ssl
from urllib.parse import unquote, urlsplit


class RedisProbeError(RuntimeError):
    pass


def _command(*parts: str) -> bytes:
    encoded = [p.encode() for p in parts]
    out = [f"*{len(encoded)}\r\n".encode()]
    for item in encoded:
        out.append(f"${len(item)}\r\n".encode() + item + b"\r\n")
    return b"".join(out)


async def _expect_ok(reader: asyncio.StreamReader, expected: bytes) -> None:
    line = await reader.readline()
    if not line:
        raise RedisProbeError("connection closed by Redis")
    if line.startswith(b"-"):
        raise RedisProbeError(line[1:].strip().decode(errors="replace"))
    if line.strip() != expected:
        raise RedisProbeError(f"unexpected reply {line.strip()!r}")


async def ping_redis(url: str, timeout: float = 2.0) -> None:
    """Raise ``RedisProbeError`` (or ``TimeoutError``/``OSError``) if Redis is unhealthy."""
    parts = urlsplit(url)
    if parts.scheme not in {"redis", "rediss"}:
        raise RedisProbeError(f"unsupported scheme {parts.scheme!r}")
    host = parts.hostname or "localhost"
    port = parts.port or 6379
    ssl_context = ssl.create_default_context() if parts.scheme == "rediss" else None
    db = parts.path.lstrip("/") or "0"

    async def _run() -> None:
        reader, writer = await asyncio.open_connection(host, port, ssl=ssl_context)
        try:
            if parts.password is not None:
                auth = (
                    _command("AUTH", unquote(parts.username), unquote(parts.password))
                    if parts.username
                    else _command("AUTH", unquote(parts.password))
                )
                writer.write(auth)
                await writer.drain()
                await _expect_ok(reader, b"+OK")
            if db != "0":
                writer.write(_command("SELECT", db))
                await writer.drain()
                await _expect_ok(reader, b"+OK")
            writer.write(_command("PING"))
            await writer.drain()
            await _expect_ok(reader, b"+PONG")
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    await asyncio.wait_for(_run(), timeout=timeout)
