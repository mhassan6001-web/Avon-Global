# Stage 1 report: core infrastructure and application shell

- Date: 2026-11-12
- Status: **Approved by the Director on 2026-11-12.** Partially verified (see §2–3).

## 1. Environment limits (affect what could be tested)

The build workspace **blocks package downloads**. FastAPI, SQLAlchemy,
Alembic, psycopg, Next.js, Framer Motion and the React type definitions could
not be installed. Docker has no daemon.

These *were* available and used: PostgreSQL 16, Redis 7, Python 3.13 with
Pydantic, Starlette and pytest, ruff, mypy, Node 22, TypeScript, esbuild,
Prettier, React 19, react-icons and headless Chromium.

**So the full stack has not been started end to end.** The integration tests,
migration run, `next build` and type check are written and wired into CI, but
were **not executed**. They run with `make check` on a machine with Docker,
or in CI.

## 2. Results: executed

| Check | Command | Result |
|-------|---------|--------|
| Backend unit tests | `pytest` (with a real Redis 7 at `TEST_REDIS_URL`) | **53 passed**, 1 skipped (the integration package, which needs FastAPI) |
| Backend lint | `ruff check .` | **Pass** (0 issues) |
| Backend format | `ruff format --check .` | **Pass** (44 files) |
| Backend types | `mypy --strict` on the 8 dependency-free modules (config, logging, request context, errors, middleware, Redis probe, readiness, schemas) | **Pass** (0 issues) |
| Backend syntax | `python -m compileall app alembic tests` | **Pass** |
| Migration DDL on real PostgreSQL 16.15 | Hand-translated SQL of migration 0001, run with `psql` | **Pass.** Table created. Defaults `not_confirmed`/`MWK` work. 3 invalid inserts rejected by CHECK constraints. "Registered" with a number accepted. `DROP TABLE` (downgrade) OK. *Note: this is not an Alembic run.* |
| Compose file | `docker compose config -q` | **Valid** |
| Frontend unit tests | `node --test` (tsx) | **15 passed**, 0 failed |
| Frontend syntax | esbuild transpile of all 34 `.ts`/`.tsx` files | **0 failures** |
| Frontend format | `prettier --check` | **Pass** |
| Rendered UI | Real components bundled with React 19 and opened in headless Chromium at 1440×900 and 390×844 | **No JavaScript errors.** Startup, Command Centre, System Status, Preferences, a module page, loading state, notifications, collapsed sidebar, API-down state, high contrast and mobile drawer all render. See `docs/stage-1-preview.png`. |
| Accessibility smoke | Playwright keyboard run | Skip link is first in tab order. The motion radio group responds to arrow keys and saves the choice. OS reduced motion maps to `data-motion="reduced"`. Motion "off" suppresses the startup overlay. |

Note on the rendered preview: Next.js and Framer Motion were replaced by
minimal stand-ins (plain elements, a hash router), and the readiness response
was **simulated**. The preview proves layout, styling, states and component
logic. It does **not** prove animations, the Next.js router or a real API
connection.

## 3. Results: not executed (pending Docker or CI)

- Backend integration tests (`tests/integration`). These cover live and ready
  endpoints against real Postgres and Redis, 503 behaviour, the error
  envelope (404/409/422/500), the OpenAPI path, the Alembic upgrade → downgrade
  → upgrade round-trip, a model/migration drift check, and DB constraint
  tests.
- `alembic upgrade head` against a database.
- API startup (`uvicorn app.main:create_app --factory`).
- `mypy app` across the whole package (needs the FastAPI and SQLAlchemy
  stubs), plus bandit and pip-audit.
- `npm run typecheck`, `npm run lint` and `npm run build`.
- Real Framer Motion animations and Next.js routing in a browser.

CI is configured to **fail if any integration test is skipped**.

## 4. Scope delivered vs requested

| Requested | Delivered |
|-----------|-----------|
| Next.js + TypeScript | Next.js 15 App Router (code, config, Dockerfile). Build not run. |
| FastAPI backend | App factory, `/api/v1` versioning, CORS, middleware |
| PostgreSQL / SQLAlchemy / Alembic | Engine and sessions, naming convention, baseline migration `0001` (`organisation_profile`), migration-state check |
| Pydantic schemas | Health schemas. Settings model. |
| Environment configuration | Validated settings with production guards. `.env.example`. |
| Logging and error handling | JSON or console logs, request IDs, redaction. Standard error envelope with 4 handlers. |
| Redis where needed | Readiness probe. Compose service. Celery deferred until a stage needs jobs. |
| Docker development environment | Compose with Postgres, Redis, API and web, plus healthchecks. Production image targets. |
| Health and readiness | `/health/live` and `/health/ready` (database, migrations, Redis) |
| App shell | Sidebar (collapsible), header, profile area, notification area, mobile drawer, bottom nav, loading, error and 404 states |
| Design system | Tokens, 10 UI components, emblem and wordmark |
| Motion system | Startup sequence, route transitions, motion and contrast preferences applied before paint |
| No fake modules | All 11 business modules are marked **Planned** and lead to scope pages. There are no sample figures. |
| Documentation | README, CLAUDE.md, PROJECT_STATUS, ROADMAP, CHANGELOG, SECURITY, docs/architecture/*, docs/security/* |

**Extra, at the Director's request during this stage:**

- `backend/app/ai/prompts/jarvis_personality.md`: stored, not wired.
- JARVIS design specification: documentation only (VOICE_AND_SOUND,
  AI_ARCHITECTURE, SECURITY_MODEL, DESIGN_SYSTEM updates).

## 5. Known gaps and risks

1. **Stage 0 documentation was not found.** It was not in the Project, past
   chats, GitHub or the visible folders on the Director's computer. Stage 1
   was built from the master instructions. If Stage 0 exists, it should be
   reconciled.
2. No lock files yet (`package-lock.json`, pinned Python requirements). These
   are generated on the first online install and committed.
3. Fonts load through `next/font/google` at build time, so the build needs
   network access.
4. No authentication. The system must not be exposed publicly before Stage 2.

## 6. How to verify on your machine

```bash
cp .env.example .env
make up          # http://localhost:3000 and http://localhost:8000/api/v1/docs
make check       # lint + all tests including integration
```
