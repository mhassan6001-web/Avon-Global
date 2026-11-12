# AVEN GLOBAL — Project status

_Last updated: 2026-11-12_

## Where we are

All fifteen stages are **built and verified in GitHub CI** on branch
`stage-3-onwards` (pull request #3, stacked on PR #2). The Director instructed
on 2026-11-12: _"approve and complete full next stages, ask questions and
needs at the end"_. Stages 3–15 therefore ran in sequence, without a stop
between stages, and questions are collected at the end of the final report
(`docs/stages-3-15-report.md`).

**Built is not production-ready.** Production needs the Director's inputs
and the checks in `docs/operations/PRODUCTION_CHECKLIST.md`. Nothing is
deployed.

| Stage | Status |
|-------|--------|
| 0 Architecture | Approved |
| 1 Foundation | Approved; CI green |
| 2 Authentication and security | Built, CI green; awaiting approval (PR #2) |
| 3 Design system, sound engine, charts, JARVIS visuals | Built, CI green |
| 4 Director dashboard and CRM | Built, CI green |
| 5 Tenders | Built, CI green |
| 6 Procurement and suppliers | Built, CI green |
| 7 Finance and accounting | Built, CI green. **Accountant sign-off required before live use.** |
| 8 Inventory and logistics | Built, CI green. GL posting of stock valuation is not automated yet. |
| 9 HR and payroll | Built, CI green. **Statutory rules must be entered and reviewed by a professional.** |
| 10 Staff communications | Built, CI green |
| 11 JARVIS AI core | Built, CI green. Uses a deterministic test provider until the Anthropic key is supplied. |
| 12 Voice | Built, CI green. STT/TTS providers and the Porcupine key are pending. |
| 13 Documents | Built, CI green. Email outbox and reminders are **not built** (no email provider yet). |
| 14 Production readiness | Documents written (`docs/operations/*`). Infrastructure not provisioned. |
| 15 Installable app (PWA) | Manifest, icons and a shell-only service worker built. A native app is not started. |

## Director decisions on record (2026-11-12)

- **JARVIS:** voice CINEMATIC, activation WAKE_WORD, sound IMMERSIVE.
  Wake-word engine: Porcupine with a paid licence. The AccessKey will come at
  the end.
- **Visual design:**
  - Grey-black and gold, with cyan only for JARVIS and live data.
  - Rich motion.
  - Charts show "No data yet" instead of fake numbers.
- **Logo:** the Director's AVEN GLOBAL artwork (`docs/brand/LOGO.md`). It
  appears in the app and on every document and letterhead.
- **Access:** department-scoped. Only the Director sees everything.
- **Security:** Director-issued reset links. 2FA for Director, Finance and
  HR/Admin.
- **Testing:** GitHub CI. The Director merges into `main`.

## Next

The Director answered the open questions on 2026-11-12. They are recorded in
`docs/DIRECTOR_DECISIONS.md` (confirmed, proposed, pending and
professional-review items) and `docs/OUTSTANDING_INFORMATION.md`.

Phase 2 is planned in `ROADMAP.md`. **Stage R (research, no purchases) and
Stage 16 (company identity, quotations and approval rules) await the
Director's approval to start.** PRs #1–#3 await review and merge.
