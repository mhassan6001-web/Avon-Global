"""Every API route must declare an access guard; public routes are an explicit allow-list."""

from __future__ import annotations

from fastapi import FastAPI

from app.platform.authz.deps import iter_guards

PUBLIC = {
    ("GET", "/api/v1/health/live"),
    ("GET", "/api/v1/health/ready"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/invitations/accept"),
    ("POST", "/api/v1/auth/password/reset"),
}
# Routes usable before two-factor verification completes.
PARTIAL = {
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/2fa/verify"),
    ("POST", "/api/v1/auth/2fa/setup"),
    ("POST", "/api/v1/auth/2fa/enable"),
}


def _routes(app: FastAPI) -> list[tuple[str, str, set[str]]]:
    """Every (method, path, guard kinds) declared by the v1 module routers."""
    from app.api.v1.router import ROUTERS

    prefix = "/api/v1"
    out = []
    for router in ROUTERS:
        for route in router.routes:
            dependant = getattr(route, "dependant", None)
            for method in getattr(route, "methods", None) or []:
                if method == "HEAD" or dependant is None:
                    continue
                kinds = {kind for kind, _ in iter_guards(dependant)}
                out.append((method, prefix + route.path, kinds))
    return out


def test_router_list_covers_every_published_endpoint(app: FastAPI) -> None:
    """ROUTERS must contain every endpoint the app actually serves."""
    published = {
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    declared = {(m, p) for m, p, _ in _routes(app)}
    assert published == declared


def test_every_route_is_guarded(app: FastAPI) -> None:
    routes = _routes(app)
    assert len(routes) > 30
    unguarded = [(m, p) for m, p, kinds in routes if not kinds]
    assert unguarded == [], f"routes without an access guard: {unguarded}"


def test_public_and_partial_routes_are_exactly_the_allow_lists(app: FastAPI) -> None:
    routes = _routes(app)
    public = {(m, p) for m, p, kinds in routes if kinds == {"public"}}
    partial = {(m, p) for m, p, kinds in routes if "partial" in kinds}
    assert public == PUBLIC
    assert partial == PARTIAL
    # Nothing else may be reachable without a full session.
    for m, p, kinds in routes:
        if (m, p) not in PUBLIC | PARTIAL:
            assert kinds & {"authenticated", "permission"}, (m, p, kinds)


def test_admin_routes_require_permissions(app: FastAPI) -> None:
    for m, p, kinds in _routes(app):
        if p.startswith("/api/v1/admin"):
            assert "permission" in kinds, (m, p)
            if m in {"POST", "PUT", "DELETE"} and not p.endswith("/audit/verify"):
                assert "step_up" in kinds, (m, p)
