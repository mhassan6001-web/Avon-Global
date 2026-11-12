"""Redis probe tests.

Uses a real Redis server when ``TEST_REDIS_URL`` is set (CI and Docker); the
error-path tests use a tiny fake server and always run.
"""

import asyncio
import os

import pytest

from app.infra.redis_probe import RedisProbeError, _command, ping_redis

REDIS_URL = os.environ.get("TEST_REDIS_URL")


def test_command_encoding() -> None:
    assert _command("PING") == b"*1\r\n$4\r\nPING\r\n"
    assert _command("AUTH", "pw") == b"*2\r\n$4\r\nAUTH\r\n$2\r\npw\r\n"


@pytest.mark.skipif(not REDIS_URL, reason="TEST_REDIS_URL not set")
def test_ping_real_redis() -> None:
    assert REDIS_URL
    asyncio.run(ping_redis(REDIS_URL, timeout=2))


def test_connection_refused() -> None:
    with pytest.raises(OSError):
        asyncio.run(ping_redis("redis://127.0.0.1:1/0", timeout=2))


def test_unsupported_scheme() -> None:
    with pytest.raises(RedisProbeError):
        asyncio.run(ping_redis("http://127.0.0.1:6379", timeout=1))


async def _fake_server(reply: bytes) -> tuple[asyncio.AbstractServer, int]:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await reader.read(64)
        writer.write(reply)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


@pytest.mark.parametrize("reply", [b"-NOAUTH Authentication required.\r\n", b"+NOPE\r\n", b""])
def test_bad_replies_raise(reply: bytes) -> None:
    async def run() -> None:
        server, port = await _fake_server(reply)
        async with server:
            await ping_redis(f"redis://127.0.0.1:{port}/0", timeout=2)

    with pytest.raises(RedisProbeError):
        asyncio.run(run())


def test_good_reply_passes() -> None:
    async def run() -> None:
        server, port = await _fake_server(b"+PONG\r\n")
        async with server:
            await ping_redis(f"redis://127.0.0.1:{port}/0", timeout=2)

    asyncio.run(run())
