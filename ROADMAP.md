# AVEN GLOBAL — Roadmap

This file is the stage order the Director set on 2026-11-12. The full wording
of each stage is in `docs/director-stage-plan.md`. **Every stage ends with a
test report and stops for Director approval.** The next stage starts only
after that approval.

| # | Stage | Status |
|---|-------|--------|
| 0 | Master architecture and blueprint (`docs/stage-0-specification.md`, received 2026-11-12, **text incomplete**) | **Approved 2026-11-12**, with reference-design decisions C1–C9 |
| 1 | Core infrastructure & application shell | **Approved 2026-11-12** |
| 2 | **Next: plan awaiting approval** (`docs/stage-2-plan.md`). Identity & security: login, hashing, reset, sessions, 2FA, roles and individual permissions, activation/suspension, login history, audit logs, rate limiting, secure file access; six initial roles; development-only test accounts |  |
| 3 | Visual experience (**apply reference decisions C1–C9**: grey-black and gold, rich motion graphics, JARVIS head with task-execution visuals): production design system, startup identity, transitions, glass/holographic panels, animated charts, JARVIS visual placeholder; original sound engine with categories, mute, quiet mode and previews | Queued |
| 4 | Director Command Centre & CRM, built from real records and calculations | Queued |
| 5 | Tender management: register, deadlines, readiness checks, awards; permitted external sources only | Queued |
| 6 | Procurement: suppliers, verification, quotations, landed cost, approvals, POs, protected bank details | Queued |
| 7 | Finance & accounting: double entry, ledger, invoices, receipts, reconciliation, multi-currency, reports, PDFs | Queued |
| 8 | Inventory & logistics: catalogue, stock movements, valuation, shipments, delivery notes, proof of delivery | Queued |
| 9 | Staff & HR: profiles, contracts, leave, payroll preparation, KPIs, reviews; salary data restricted | Queued |
| 10 | Staff communications: messaging, channels, announcements, tasks, reports, live updates | Queued |
| 11 | JARVIS AI core: Claude via provider abstraction, permission-filtered tools, logs, cost tracking | Queued |
| 12 | JARVIS voice: push-to-talk, STT/TTS, streaming, interruptions, original voice | Queued |
| 13 | Documents & integrations: PDF/Word/Excel, email, calendar, storage, reminders | Queued |
| 14 | Production readiness: full testing, deployment, backups, restore tests, monitoring, launch report | Queued |
| 15 | Mobile: installable PWA first, then an assessment of native iOS/Android | Queued |

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
