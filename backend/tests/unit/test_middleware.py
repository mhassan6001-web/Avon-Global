"""Request-context middleware tested against a bare Starlette app."""

import pytest

pytest.importorskip("starlette.testclient")

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.middleware import RequestContextMiddleware
from app.core.request_context import get_request_id


async def echo(_: Request) -> JSONResponse:
    return JSONResponse({"request_id": get_request_id()})


@pytest.fixture
def client() -> TestClient:
    app = Starlette(routes=[Route("/echo", echo)])
    app.add_middleware(RequestContextMiddleware)
    return TestClient(app)


def test_generates_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/echo")
    rid = response.headers["x-request-id"]
    assert len(rid) == 32
    assert response.json()["request_id"] == rid
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_propagates_valid_incoming_id(client: TestClient) -> None:
    response = client.get("/echo", headers={"X-Request-ID": "trace-abc-123"})
    assert response.headers["x-request-id"] == "trace-abc-123"


def test_replaces_unsafe_incoming_id(client: TestClient) -> None:
    response = client.get("/echo", headers={"X-Request-ID": "bad id <script>"})
    assert response.headers["x-request-id"] != "bad id <script>"
