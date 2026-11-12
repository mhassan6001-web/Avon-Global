# Changelog

## [0.1.0] — 2026-11-12 — Stage 1: Core infrastructure (approved 2026-11-12)

### Added
- FastAPI backend (`app.main:create_app` factory) with an API versioned under `/api/v1`.
- Environment configuration validated at startup, with production-safety guards.
- Structured logging: JSON in production, console in development. Includes
  request IDs and redaction of secret-looking fields.
- Standard error envelope and handlers for application, validation, HTTP and
  unexpected errors. Submitted values are never echoed back.
- Request-context middleware: `X-Request-ID`, access log, security headers.
- SQLAlchemy 2 engine/session management (psycopg 3) and a declarative base
  with a constraint naming convention.
- Alembic setup and baseline migration `0001`: the `organisation_profile`
  table, a configurable company identity with no rows inserted.
- Health endpoints: `/health/live` and `/health/ready` (database, migration
  state, Redis).
- Dependency-free Redis readiness probe.
- Next.js 15 + TypeScript web app shell:
  - sidebar (collapsible) and mobile drawer
  - header with live platform status
  - notification area and profile area
  - bottom navigation on phones
  - loading, error and not-found states
- AVEN GLOBAL design system: tokens, glass panels, buttons, badges, status
  dots, skeletons, empty states, page headers and segmented controls.
- An original AVEN GLOBAL emblem and wordmark.
- Motion system: an animated startup sequence (once per session, skippable),
  route transitions, motion intensity (match device/full/reduced/off) and a
  high-contrast mode.
- Pages: Command Centre (live status, delivery stages, module overview),
  System Status, Display Preferences, and information pages for planned modules.
- Docker development environment, Makefile and CI workflow.
- Documentation: README, CLAUDE.md, PROJECT_STATUS, ROADMAP, SECURITY, ADR 0001,
  design system, the Stage 1 report, and the Director's stage plan.
- JARVIS personality, supplied by the Director: stored at
  `backend/app/ai/prompts/jarvis_personality.md` (not used until Stage 11).

## [0.1.0-docs] — 2026-11-12 — JARVIS design specification (documentation only, approved 2026-11-12)

### Added
- `docs/jarvis-design-specification.md`: the Director's confirmed decisions
  (voice CINEMATIC, activation WAKE_WORD, sound IMMERSIVE), verbatim.
- `docs/architecture/VOICE_AND_SOUND.md`: covers:
  - voice, wake-word and sound architecture
  - researched platform limits (web and PWA listening is foreground-only)
  - wake-word engine options and their licence constraints
  - how the decisions fit existing requirements
  - testable acceptance criteria (WW, MP, VO, SC, SV, PC)
- `docs/architecture/AI_ARCHITECTURE.md`: JARVIS components, tool rules and
  the execution chain.
- `docs/security/SECURITY_MODEL.md`: the security model, including the AI and
  voice threat model.

### Changed
- `CLAUDE.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, `SECURITY.md` and
  `docs/architecture/DESIGN_SYSTEM.md` now reference the confirmed decisions.
- Docs reorganised: `docs/design-system.md` became
  `docs/architecture/DESIGN_SYSTEM.md`, and the ADR moved into
  `docs/architecture/`.

No existing requirement was removed.

## [0.1.0-docs.2] — 2026-11-12 — Stage 0 blueprint and reference-image register (approved 2026-11-12)

### Added
- `docs/stage-0-specification.md`: the Director's Stage 0 text, verbatim.
  **The received text ends at "I. STAFF COMMUNICATIONS".**
- `docs/architecture/MASTER_ARCHITECTURE.md`: the Stage 0 blueprint covering:
  - modules A–I and shared platform services
  - data and finance architecture
  - WebSockets, Celery, storage and deployment
  - non-functional targets
  - reconciliation with the Stage 1 code
- `docs/reference-image-fidelity-instruction.md`: the Director's instruction,
  verbatim.
- `docs/architecture/REFERENCE_IMAGE_SPECIFICATION.md`: covers:
  - the inspection record and register for all 8 images
  - component-to-reference mapping
  - Stage 1 deviation analysis
  - conflicts C1–C9
  - the per-screen QA procedure
- `design-references/`: the 8 reference images and a side-by-side comparison
  of Stage 1 against ref 08.

### Changed
- Wake-word engine decided: Picovoice Porcupine, paid licence, with the
  AccessKey supplied later (`VOICE_AND_SOUND.md`, `ROADMAP.md`).
- `CLAUDE.md`: added the visual design rule and the new required reading.

### Director decisions recorded (2026-11-12)
- Stage 0 approved.
- Reference-design decisions C1–C9 approved:
  - grey-black and gold base, with navy as a secondary depth tone
  - rich motion graphics within the motion settings
  - a JARVIS particle head with real task-execution connection visuals
  - JARVIS daily briefing, as text and speech
  - HUD and serif typefaces
- Recorded in `REFERENCE_IMAGE_SPECIFICATION.md` §6.1, `AI_ARCHITECTURE.md`
  §5–6 and `DESIGN_SYSTEM.md`.
