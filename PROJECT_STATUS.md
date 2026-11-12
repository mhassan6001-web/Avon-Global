# AVEN GLOBAL — Project status

_Last updated: 2026-11-12_

## Current stage

**Stage 1: approved by the Director on 2026-11-12.** Report:
`docs/stage-1-report.md`.

The **JARVIS specification documents were also approved on 2026-11-12.**

**Stage 0 (master architecture) was approved on 2026-11-12**, together with
reference-design decisions C1–C9 (grey-black and gold, rich motion graphics,
the JARVIS head with task-execution visuals, and JARVIS briefings).

The supplied Stage 0 text is incomplete (it ends at "I. STAFF
COMMUNICATIONS"). Any remaining sections will be reconciled when received.

The **Stage 2 plan** (`docs/stage-2-plan.md`) is also awaiting decisions. No
Stage 2 code has been written.

## What exists

- **Backend:**
  - FastAPI app versioned at `/api/v1`
  - validated configuration, structured logging and the error envelope
  - request IDs and security headers
  - SQLAlchemy and Alembic, with baseline migration `0001` (`organisation_profile`)
  - health and readiness endpoints (database, migration state, Redis)
- **Frontend:**
  - Next.js shell: sidebar, header, status, notifications, profile, mobile navigation
  - AVEN GLOBAL design system and emblem
  - startup sequence, route transitions, motion and contrast preferences
  - Command Centre, System Status, Preferences and planned-module pages
- **Tooling:** Docker Compose for development, Makefile, CI workflow.
- **Stored for later:** the JARVIS personality prompt (Stage 11), the
  Director's stage plan, and the JARVIS design specification.

## What does not exist yet

Authentication and every business module: Director dashboard data, CRM,
tenders, procurement, finance, inventory, logistics, HR, communications,
documents and JARVIS. They appear in the navigation as **Planned** only.

## Verification status

- **Executed:**
  - 53 backend unit tests, using a real Redis
  - 15 frontend unit tests
  - ruff, scoped mypy, Prettier and esbuild syntax checks
  - migration DDL on real PostgreSQL 16
  - headless-browser render of the shell
- **Not executed (no package downloads in the build workspace):**
  - backend integration tests and the Alembic run
  - API startup
  - `next build`, `tsc` and ESLint

  These run in CI and with `make check`.

## Decisions needed from the Director

1. **Stage 2 plan** (`docs/stage-2-plan.md` §7):
   - the role matrix
   - password reset before email
   - the test-execution route (**blocking**)
   - the 2FA policy
2. Optional: the rest of the Stage 0 text, if it exists.
3. Before Stage 12: the wake phrase, the TTS provider shortlist and the audio
   source. *(Wake-word engine decided: Porcupine paid licence, with the
   AccessKey to come later.)*

## Next stage (after approval)

**Stage 2: Identity and security.** Implementation starts after the plan is
approved and the test-execution route is in place.
