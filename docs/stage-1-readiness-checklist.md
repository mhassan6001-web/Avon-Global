# Stage 1 readiness checklist (Stage 0 §11)

Stage 1 was built and approved before the full Stage 0 text arrived. This
checklist confirms Stage 1 satisfies the Stage 0 blueprint. **Evidence is
from executed GitHub CI runs** on `mhassan6001-web/Avon-Global`
(PR #1, branch `stage-1-baseline`), not from claims.

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Repository on GitHub, with Director-controlled `main` | ✔ | PR #1 is open. Merge is the Director's decision. |
| 2 | Backend skeleton (FastAPI, `/api/v1`, Pydantic) | ✔ | CI: mypy "no issues found in 29 source files" |
| 3 | Configuration validated, production guards | ✔ | Unit tests in the 62-test pytest run |
| 4 | Structured logging, request IDs, error envelope | ✔ | Unit and integration tests |
| 5 | PostgreSQL + SQLAlchemy + Alembic | ✔ | CI: `alembic downgrade base → upgrade head → check` passed, head `0001` |
| 6 | Integration tests on real PostgreSQL 16 and Redis 7 | ✔ | CI: **9 integration tests passed**, **62 passed** in total |
| 7 | Health and readiness endpoints | ✔ | Integration tests. CI startup step (live and ready probes return 200). |
| 8 | Redis available | ✔ | Readiness check plus probe tests |
| 9 | Next.js + TypeScript shell, design tokens, motion system | ✔ | CI: `tsc` clean, ESLint clean, **15/15** frontend tests, `next build` compiled |
| 10 | Docker development environment | ✔ (config) | `docker compose config` valid. A full `make up` has not been run by Claude (no Docker daemon). |
| 11 | CI pipeline: lint, types, security (bandit, pip-audit), tests, migrations, startup, build | ✔ | Commit check-runs, backend ✔ and frontend ✔ |
| 12 | Secrets not committed, `.env` ignored | ✔ | `.gitignore` and `.dockerignore` |
| 13 | Documentation set (Stage 0 §9) | ✔ | 14 documents present (see CHANGELOG) |

**Known non-blocking items:**

- **8 pytest warnings:**
  - Alembic `path_separator` deprecation
  - the Starlette TestClient `httpx` deprecation

  They will be fixed at the start of Stage 2.
- The GitHub Actions Node 20 deprecation was addressed by moving to the
  actions' Node 24 versions.
