# AVEN GLOBAL

The AVEN GLOBAL business operating system is a single cloud-hosted platform for the company's
procurement, sales, tenders, finance, inventory, logistics, HR, communications
and executive AI (JARVIS). It will be used on Windows, Mac, iPhone and Android.

**Current state: Stage 1 (core infrastructure and application shell), awaiting
Director approval.** No business module is built yet. See `PROJECT_STATUS.md`.

## Architecture

| Layer      | Technology                                          |
|------------|-----------------------------------------------------|
| Web app    | Next.js 15 (App Router), React 19, TypeScript, Framer Motion |
| API        | Python 3.12, FastAPI, Pydantic v2, versioned at `/api/v1` |
| Database   | PostgreSQL 16, SQLAlchemy 2, Alembic migrations     |
| Cache/jobs | Redis 7 (Celery workers arrive with background jobs) |
| Runtime    | Docker; one modular-monolith API (docs/architecture/ADR-0001)         |

The browser only ever calls same-origin `/api/v1/*`. Next.js proxies those
requests to the API (`BACKEND_INTERNAL_URL`), so the API host is never exposed.

## Run it (development)

Requirements: Docker Desktop (Windows/Mac) or Docker Engine + Compose v2.

```bash
make up          # copies .env.example → .env, builds and starts everything
```

| Service   | URL                                        |
|-----------|--------------------------------------------|
| Web app   | http://localhost:3000                      |
| API docs  | http://localhost:8000/api/v1/docs          |
| Liveness  | http://localhost:8000/api/v1/health/live   |
| Readiness | http://localhost:8000/api/v1/health/ready  |

The development backend applies migrations on start (`scripts/start-dev.sh`).
In production, migrations run as a separate release step, never on every start.

## Checks

```bash
make lint            # ruff, ruff format, mypy, eslint, tsc, prettier
make test            # backend unit + integration (real Postgres/Redis), frontend tests
```

CI (`.github/workflows/ci.yml`) runs the same checks plus bandit, pip-audit, a
migration round-trip, an API startup test and `next build`. CI fails if any
integration test is skipped.

## Health endpoints

- `GET /api/v1/health/live`: the process is up. It makes no dependency calls.
- `GET /api/v1/health/ready`: checks database connectivity, that the schema is
  at the latest Alembic revision, and that Redis is reachable. It returns 503
  if any required check fails. Responses never include hostnames, credentials
  or driver errors.

Every response carries an `X-Request-ID` header that matches the server logs.
All errors use one envelope:
`{"error": {"code", "message", "details?", "request_id"}}`.

## Configuration

All configuration comes from environment variables (see `.env.example`) and is
validated at startup. With `APP_ENV=production` the API refuses to start if:

- the database or Redis host is local
- the development password is in use
- a CORS origin is non-HTTPS or local
- logs are not JSON
- the log level is DEBUG

## Documents

`PROJECT_STATUS.md`, `ROADMAP.md`, `CHANGELOG.md`, `SECURITY.md`,
`docs/architecture/DESIGN_SYSTEM.md`, `docs/architecture/`, `docs/security/`, `docs/stage-1-report.md`,
`docs/director-stage-plan.md`.
