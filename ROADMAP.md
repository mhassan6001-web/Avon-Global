# AVEN GLOBAL — Roadmap

This file is the stage order the Director set on 2026-11-12. The full wording
of each stage is in `docs/director-stage-plan.md`. On 2026-11-12 the Director instructed that Stages 3–15 run consecutively,
with questions collected at the end (`docs/stages-3-15-report.md`).

| # | Stage (Stage 0 §10 naming) | Depends on | Key scope | Status |
|---|------|-----------|-----------|--------|
| 0 | Architecture and project blueprint | — | `docs/architecture/*`, `docs/security/*` (14 required documents) | **Approved 2026-11-12** |
| 1 | Repository foundation and development environment | 0 | FastAPI/Next.js foundation, config, logging, errors, health, Alembic, Docker, CI | **Approved 2026-11-12. CI green on GitHub** (`docs/stage-1-readiness-checklist.md`) |
| 2 | Authentication and security | 1 | Login, Argon2id, sessions, Director-issued reset links, 2FA, department-scoped roles, overrides, suspension, login history, audit log, rate limiting, secure files, module K admin basics | **Built, CI green.** Awaiting approval (PR #2). |
| 3 | Core design system and interface | 1, 2 (sign-in screens) | Reference-faithful grey-black and gold system (C1–C9), rich motion graphics, charts, JARVIS placeholder head, sound engine and settings | **Built, CI green** (PR #3) |
| 4 | Director dashboard and CRM | 2, 3 | Command Centre from real records, CRM, quotations, contracts, search, outbox and events | **Built, CI green** |
| 5 | Tender management | 2, 3, 4 (CRM organisations) | Register, government, NGO and UN sources (permitted only), bid costing, checklists, deadline alerts, Celery | **Built, CI green** |
| 6 | Procurement and suppliers | 2, 3 | Suppliers, verification, quotations, landed cost, PRs and POs, encrypted bank details with dual control, supplier performance | **Built, CI green** |
| 7 | Finance and accounting | 4, 6 | Double-entry, periods, invoices, receipts, bills, payments, reconciliation, FX, tax configuration, reports, finance PDFs. **Accountant sign-off gate.** | **Built, CI green.** Accountant sign-off pending. |
| 8 | Inventory and logistics | 6, 7 | Stock movements, valuation, shipments, customs, deliveries, proof of delivery | **Built, CI green** |
| 9 | Human resources | 2, 7 | Employees, contracts, leave, attendance, payroll preparation (configurable statutory rules, professional sign-off), KPIs | **Built, CI green.** Statutory review pending. |
| 10 | Staff communications | 2, 9 | Messaging, channels, announcements, tasks, reports, WebSockets, AI-message labelling | **Built, CI green** |
| 11 | JARVIS AI integration | 4–10 (tools gated per module) | Provider abstraction, ActionGateway, tools, briefings, usage ledger, task-execution visuals | **Built, CI green.** Anthropic key pending. |
| 12 | Voice activation and immersive audio | 3, 11 | CINEMATIC voice, Porcupine wake word (Director's key), push-to-talk, STT/TTS streaming | **Built, CI green.** STT/TTS and Porcupine key pending. |
| 13 | Documents and external integrations | 4–10 | Document Centre (J), email, calendar, reminders, notifications | **Documents built, CI green.** Email, calendar and reminders wait for providers. |
| 14 | Cloud deployment and production readiness | all | Hosting, HTTPS, secrets, backups and restore tests, monitoring, UAT, launch report. **Director approval to deploy.** | **Runbooks written.** Not provisioned; deploy only with Director approval. |
| 15 | Mobile experience and native application planning | 14 | PWA (icons, splash, push), mobile layouts (ref 06), then a native assessment | **PWA built, CI green.** Native assessment not started. |

## Phase 2 (proposed 2026-11-12 from the Director's answers; **each stage needs approval before it starts**)

| # | Stage | Scope | Status |
|---|-------|-------|--------|
| R | Research and comparisons (no purchases) | Voice shortlist with samples; Porcupine "Hey JARVIS" licence and compatibility check; preliminary trademark search (Malawi and international); Azure South Africa North costing against alternatives; monitoring comparison; domain availability; Reserve Bank of Malawi rate source | Awaiting approval |
| 16 | Company identity, quotations and approval rules | Editable address, phone, TPIN and VAT fields with print approval (hidden until approved); letterhead from these fields; **quotations** (records and PDF/Word); configurable approval limits and the second-approver block; JARVIS model routing (Sonnet default, Opus advanced) | Awaiting approval |
| 17 | Statements and supplier documents | Customer account statements; invoice and receipt layout refinements; supplier quotation documents | Queued |
| 18 | Perpetual inventory accounting | Real-time ledger entries for receipts, transfers, sales, deliveries, returns, damage and adjustments; monthly valuation and reconciliation; live posting gated on accountant approval of the method | Queued |
| 19 | Exchange rates and date-effective payroll | Daily Reserve Bank of Malawi rates where a reliable source exists, with source records; date-effective statutory tables | Queued |
| 20 | Microsoft 365 integration | Email outbox, Outlook calendar, reminders and document storage through a replaceable interface; connected only with approval | Queued |
| 21 | Retention and archival | Configurable policies, legal hold, authorised deletion procedure | Queued (after legal confirmation) |
| 22 | Contracts and tender packs | Contracts and service agreements; EOI, RFQ and RFP packs with company documents | Queued |
| 23 | Azure provisioning and launch | Only after cost approval, the accountant's review and user acceptance tests | Queued |

Decisions and pending information: `docs/DIRECTOR_DECISIONS.md` and
`docs/OUTSTANDING_INFORMATION.md`.

**Additional work identified (folded into stages, not new stages):**

- **Stage 2:** an accountant and statutory-review process is set up early
  (who signs off tax and payroll configuration).
- **Stage 14:** a legal check of the "JARVIS" name.

## Notes recorded for later stages

- **Stage 2** must also build the API for `organisation_profile` (legal name,
  registration status). Only the Director may edit it.
- **Stage 3** extends the Stage 1 motion system and preferences (motion and
  contrast are already built) instead of replacing them.
- **JARVIS design decisions** (confirmed 2026-11-12; specification documents approved 2026-11-12): voice `CINEMATIC`,
  activation `WAKE_WORD` and sound `IMMERSIVE`. See
  `docs/architecture/VOICE_AND_SOUND.md`.
  - **Stage 3** builds the Immersive/Balanced/Quiet sound engine and the
    settings panel (SC-01–SC-07).
  - **Stage 12** builds the CINEMATIC voice, the on-device wake word with
    consent, push-to-talk, and the JARVIS visual states (WW-, MP-, VO- and
    SV- criteria).
  - **Stage 15** assesses native background wake word (Android foreground
    service, iOS restrictions) without promising it.
  - **Wake-word engine decided:** Porcupine, paid licence. The AccessKey
    will be supplied at the end of development.
  - **Still to decide before Stage 12:** wake phrase, TTS provider
    shortlist, and audio source.
- **Reference images are the primary visual specification** (instruction of
  2026-11-12).
  - **Stage 3** must bring the shell and components into line with
    `docs/architecture/REFERENCE_IMAGE_SPECIFICATION.md`, using the per-screen
    side-by-side procedure.
  - Every later screen follows its mapped reference.
- **Stage 11** loads `backend/app/ai/prompts/jarvis_personality.md` as the
  JARVIS system prompt. That file is stored but not used yet.
- Celery workers are added with the first stage that needs background jobs
  (expected in Stage 10 or 13).
