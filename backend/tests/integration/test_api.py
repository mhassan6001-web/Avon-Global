from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.v1.endpoints.health import get_readiness_checks
from app.core.errors import ConflictError
from app.services.readiness import ReadinessCheck


def test_live(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "AVEN GLOBAL"
    assert body["environment"] == "test"
    assert response.headers["x-request-id"]


def test_ready_against_real_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    body = response.json()
    checks = {c["name"]: c for c in body["checks"]}
    assert checks["database"]["status"] == "ok"
    assert checks["migrations"]["status"] == "ok"
    assert checks["migrations"]["detail"] == "revision 0001"
    # Redis is required by default; its result depends on TEST_REDIS_URL being reachable.
    expected = 200 if checks["redis"]["status"] == "ok" else 503
    assert response.status_code == expected


def test_ready_returns_503_when_required_dependency_fails(client: TestClient) -> None:
    async def broken() -> str | None:
        raise ConnectionError("db down")

    client.app.dependency_overrides[get_readiness_checks] = lambda: [  # type: ignore[attr-defined]
        ReadinessCheck("database", broken)
    ]
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.app.dependency_overrides.clear()  # type: ignore[attr-defined]
    assert response.status_code == 503
    assert response.json()["status"] == "failing"
    assert "db down" not in response.text


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["request_id"] == response.headers["x-request-id"]


class _Payload(BaseModel):
    amount: int


def _attach_probe_routes(client: TestClient) -> None:
    router = APIRouter()

    @router.post("/_probe/validate")
    async def validate(payload: _Payload) -> dict[str, int]:
        return {"amount": payload.amount}

    @router.get("/_probe/conflict")
    async def conflict() -> None:
        raise ConflictError("Already approved.", code="already_approved")

    @router.get("/_probe/crash")
    async def crash() -> None:
        raise RuntimeError("unexpected")

    client.app.include_router(router, prefix="/api/v1")  # type: ignore[attr-defined]


def test_error_handlers(client: TestClient) -> None:
    _attach_probe_routes(client)

    invalid = client.post("/api/v1/_probe/validate", json={"amount": "not-a-number"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert "not-a-number" not in invalid.text

    conflict = client.get("/api/v1/_probe/conflict")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "already_approved"

    crash = client.get("/api/v1/_probe/crash")
    assert crash.status_code == 500
    error = crash.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"] == crash.headers["x-request-id"]


def test_openapi_is_versioned(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    assert "/api/v1/health/ready" in schema["paths"]
