import asyncio

from app.schemas.health import CheckStatus, ReadinessResponse
from app.services.readiness import ReadinessCheck, evaluate


async def _ok() -> str | None:
    return "fine"


async def _fail() -> str | None:
    raise ConnectionError("password=secret host=db.internal")


async def _slow() -> str | None:
    await asyncio.sleep(5)
    return None


def test_all_required_ok() -> None:
    status, results = asyncio.run(evaluate([ReadinessCheck("db", _ok)], timeout=1))
    assert status is CheckStatus.OK
    assert results[0].detail == "fine"
    assert results[0].latency_ms is not None


def test_required_failure_makes_not_ready_without_leaking_detail() -> None:
    status, results = asyncio.run(
        evaluate([ReadinessCheck("db", _ok), ReadinessCheck("redis", _fail)], timeout=1)
    )
    assert status is CheckStatus.FAILING
    failing = next(r for r in results if r.name == "redis")
    assert failing.status is CheckStatus.FAILING
    assert failing.detail == "unavailable"
    assert "secret" not in failing.model_dump_json()


def test_optional_failure_keeps_ready() -> None:
    status, _ = asyncio.run(
        evaluate([ReadinessCheck("db", _ok), ReadinessCheck("redis", _fail, required=False)], 1)
    )
    assert status is CheckStatus.OK


def test_timeout_reported() -> None:
    status, results = asyncio.run(evaluate([ReadinessCheck("db", _slow)], timeout=0.05))
    assert status is CheckStatus.FAILING
    assert results[0].detail == "timed out"


def test_response_schema_serialises() -> None:
    _, results = asyncio.run(evaluate([ReadinessCheck("db", _ok)], timeout=1))
    body = ReadinessResponse(
        status=CheckStatus.OK,
        service="AVEN GLOBAL",
        version="0.1.0",
        environment="test",
        timestamp="2026-11-12T00:00:00Z",  # type: ignore[arg-type]
        checks=results,
    ).model_dump(mode="json")
    assert body["checks"][0]["name"] == "db"
    assert body["status"] == "ok"
