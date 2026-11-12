# AVEN GLOBAL — working rules for Claude

The authoritative, full master instructions live in the **"Avon Global" claude.ai
Project instructions**. This file restates the rules that govern day-to-day work in
this repository. If the two ever disagree, the Project instructions win; raise
the conflict with the Director.

## Product

- Name: **AVEN GLOBAL**. Never use "2050" in any name, title or branding.
- Malawi-based procurement, supplies, sourcing, import/export and distribution
  business. HQ Lilongwe. Markets: Malawi, South Africa, Zambia.
- The legal company name and registration status are configurable data
  (`organisation_profile`). Never claim registration is complete.
- Never invent customers, employees, contracts, tender awards, suppliers,
  licences, tax numbers or financial figures. Demo data must be clearly
  labelled development-only.

## Stack (do not change without a documented decision)

Next.js + TypeScript + Framer Motion · Python FastAPI + Pydantic ·
PostgreSQL + SQLAlchemy 2 + Alembic · Redis (+ Celery later) · WebSockets ·
Docker · Anthropic Claude via a provider-independent AI layer.
**No Supabase. No Vercel. Localhost is never production.** Modular monolith
(see `docs/architecture/ADR-0001-modular-monolith.md`).

## Method for every stage

Before: read this file, `PROJECT_STATUS.md`, `ROADMAP.md` and
`docs/director-stage-plan.md`, `docs/jarvis-design-specification.md`,
`docs/stage-0-specification.md`, `docs/architecture/SYSTEM_ARCHITECTURE.md`,
`DATABASE_DESIGN.md` and `REFERENCE_IMAGE_SPECIFICATION.md`, then inspect
the code. Present a plan
(files, database changes, acceptance tests) for approval.

After approval: implement only the approved scope, then run formatting,
linting, type checks, unit tests, integration tests, security checks,
migration tests and a startup test. **Report exact results. Never claim a test
passed unless it was executed.** Never present visual mockups as working
features. No destructive migrations or data deletion without explicit approval
and a verified backup. Update README, PROJECT_STATUS, ROADMAP, CHANGELOG and
SECURITY docs. **Stop for Director approval at the end of every stage.**

## Non-negotiable controls

- Permissions are enforced in the backend, never by hiding buttons.
- Nobody approves their own restricted financial transaction.
- Payroll, financial data and supplier bank details are restricted.
- Posted financial records are never silently changed or deleted; corrections
  use reversals and credit notes. Tax rates are configuration, never hardcoded.
- JARVIS never runs arbitrary SQL. Every AI action passes authentication →
  permission → validation → business rules → approval → execution → audit.
  AI never initiates payments, changes supplier bank details, submits tenders
  or approves its own requests. JARVIS's personality:
  `backend/app/ai/prompts/jarvis_personality.md`.
- Audio and animation are always optional, and reduced-motion is respected.

## Confirmed JARVIS design decisions (Director, 2026-11-12)

Voice profile `CINEMATIC` · activation mode `WAKE_WORD` · sound profile
`IMMERSIVE`. These are product requirements. Full text:
`docs/jarvis-design-specification.md`. Architecture, platform limits and
acceptance criteria: `docs/architecture/VOICE_AND_SOUND.md` and
`docs/architecture/AI_ARCHITECTURE.md`.

- Wake-word detection is on-device, off by default, opt-in with recorded
  consent, and push-to-talk is always available.
- Never promise background or locked-screen listening where the platform
  forbids it. Web and PWA listening is foreground-only.
- A recognised voice never authorises a restricted action.
- All audio is original or properly licensed and recorded in
  `docs/legal/AUDIO_LICENCES.md`.
- Never imitate an actor, character or copyrighted voice.
- "2050-inspired" is a visual direction only. The product is AVEN GLOBAL.
- No hidden employee surveillance.

## Visual design rule (Director, 2026-11-12)

The images in `design-references/` are the **primary visual specification**
(`docs/reference-image-fidelity-instruction.md`).

Before building any screen:

1. Find its mapped reference in
   `docs/architecture/REFERENCE_IMAGE_SPECIFICATION.md` §4.
2. Build it.
3. Compare screenshots side by side at matching viewports.
4. Fix the deviations, then mark the screen complete.

Never claim pixel-perfect accuracy. Never copy third-party names, logos,
photos or fake statistics that appear in the references.

## Repository map

```text
design-references/  Director's visual reference images (primary design spec)
backend/   FastAPI app (app/), Alembic migrations, tests (unit/, integration/)
frontend/  Next.js app (src/app, src/components, src/lib)
docs/      architecture/ (ADRs, design system, AI, voice & sound), security/,
           stage reports, Director's stage plan, JARVIS design specification
```

## Document index (Stage 0)

| Topic | Document |
|-------|----------|
| System | `docs/architecture/SYSTEM_ARCHITECTURE.md` |
| Data | `DATABASE_DESIGN.md` |
| AI | `AI_ARCHITECTURE.md` |
| Voice and audio | `VOICE_AND_SOUND.md` |
| Design | `DESIGN_SYSTEM.md` and `REFERENCE_IMAGE_SPECIFICATION.md` |
| Deployment | `DEPLOYMENT_ARCHITECTURE.md` |
| Integrations | `INTEGRATION_STRATEGY.md` |
| Security | `docs/security/SECURITY_MODEL.md` |

Run everything with `make up` and `make check` (see README). **GitHub CI on
`mhassan6001-web/Avon-Global` is the verification environment.** Results are
read from the commit's check annotations. The Director merges into `main`.
