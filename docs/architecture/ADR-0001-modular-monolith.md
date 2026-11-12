# ADR 0001 — Modular monolith with a same-origin web proxy

- Status: Accepted (approved with Stage 1, 2026-11-12)
- Date: 2026-11-12

## Context

AVEN GLOBAL needs one central backend and database for every device. The
business modules (finance, procurement, CRM and others) share transactions,
permissions and audit trails. The team is small, and correctness matters more
than independent scaling.

## Decision

1. **One FastAPI application.** Each business area is a package under
   `app/modules/<name>/` (models, schemas, services, router) and is registered
   in `app/api/v1/router.py`. Modules call each other through service
   functions, never through each other's tables directly.
2. **One PostgreSQL database and one Alembic history.** All models are
   imported in `app/db/models.py`.
3. **API versioning by path** (`/api/v1`). Breaking changes go into `/api/v2`.
4. **Same-origin proxy.** The browser calls `/api/v1/*` on the web origin and
   Next.js forwards those calls to the API. This avoids exposing the API host,
   removes CORS for the web app, and lets session cookies stay first-party in
   Stage 2.
5. **Sync SQLAlchemy sessions in thread-pooled endpoints**, with async only
   where it helps (health probes, and WebSockets later). This keeps
   transactions simple and accountant-reviewable code readable.

## Consequences

- Single deployment unit, simple transactions and simple audit.
- Splitting a module out later needs its service boundary kept clean. Code
  review enforces this.
- Microservices are not used unless a later ADR documents a concrete reason.
