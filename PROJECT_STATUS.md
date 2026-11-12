# AVEN GLOBAL — Project status

_Last updated: 2026-11-12_

## Where we are

| Stage | Status |
|-------|--------|
| 0: Architecture and blueprint | Approved 2026-11-12. All **14 required documents** now completed from the full Stage 0 text. **Awaiting Director review.** |
| 1: Repository foundation | **Approved, and verified green in GitHub CI** (PR #1 on `mhassan6001-web/Avon-Global`): 62 backend tests including 9 integration tests on real PostgreSQL and Redis, migration round-trip, mypy clean, 15 frontend tests, `next build`. See `docs/stage-1-readiness-checklist.md`. |
| 2: Authentication and security | **Plan approved with Director decisions** (`docs/stage-2-plan.md`). Waiting for Stage 0 review, per the Stage 0 rule "STOP after Stage 0". |

## Director decisions on record (2026-11-12)

- **JARVIS:** voice CINEMATIC, activation WAKE_WORD, sound IMMERSIVE.
- **Wake-word engine:** Porcupine, paid licence. The AccessKey will be
  supplied at the end.
- **Visual design:**
  - Reference images are the primary specification.
  - Grey-black and gold, with navy as depth.
  - Rich motion graphics.
  - JARVIS particle head with task-execution visuals.
  - JARVIS daily briefings.
  - Serif and HUD typefaces.
  - Dark only.
- **Access:** department-scoped. Only the Director (Muhammad) sees
  everything. User administration is Director only.
- **Security:** Director-issued one-time reset links until email exists. 2FA
  mandatory for Director, Finance and HR/Admin.
- **Testing:** GitHub CI on the Director's repository. The Director merges
  into `main`.

## What exists

- **Backend:** FastAPI, config, logging, errors, health, SQLAlchemy and
  Alembic (`0001`).
- **Frontend:** Next.js shell and design foundation.
- **Tooling:** Docker Compose, Makefile, CI.
- **Documentation:** Stage 0 architecture set (SYSTEM, DATABASE, AI, VOICE &
  SOUND, DESIGN, SECURITY MODEL, DEPLOYMENT, INTEGRATION, REFERENCE IMAGE),
  roadmap, readiness checklist.
- No business module is built.

## Open decisions (none block Stage 2)

See `docs/architecture/SYSTEM_ARCHITECTURE.md` §13:

- hosting provider and region
- error tracker
- email provider
- STT/TTS providers
- wake phrase
- second approver for Director-initiated requests
- FX source
- payroll and tax rules, and the accountant who signs them off
- SMS or WhatsApp
- message retention

## Next

On Director approval of the Stage 0 documents, **Stage 2 implementation
begins**, delivered as a pull request with CI evidence.
