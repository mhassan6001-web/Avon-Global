# Stages 3–15: report and open questions

_2026-11-12 · branch `stage-3-onwards` · pull request #3 (based on PR #2)_

The Director's instruction: _"approve and complete full next stages, ask
questions and needs at the end."_ The stages ran in sequence without a stop
between them, and every result below comes from GitHub CI runs. **Nothing is
deployed.** Built does not mean production-ready.

## Verification (GitHub CI, final commit of this branch)

| Check | Result |
|-------|--------|
| Backend: ruff, mypy (strict), bandit, pip-audit | Clean |
| Backend tests (unit + integration on real PostgreSQL 16 and Redis) | **205 passed** (99 integration) |
| Migrations | `downgrade base` → `upgrade head` → `alembic check`: no drift, head `0013` |
| Startup | `/health/live` 200, `/health/ready` 200 (database, migrations, Redis) |
| Frontend: ESLint (0 warnings), TypeScript, unit tests, `next build` | **64/64** unit tests; lint, types and build pass |
| Browser end-to-end tests (Playwright, Chromium, real stack) | **26/26 passed** |

Measured on commit `737e40b`. The commits after it change only documentation and the in-app roadmap labels; they are re-checked by CI on the pull request.

## What was built

| Stage | Delivered | Limits |
|-------|-----------|--------|
| 3 Design system | Sound engine (original, synthesised), settings, charts with honest empty states, JARVIS visuals, account-synced preferences | Side-by-side reference screenshots for every screen still need manual review |
| 4 Director and CRM | Command Centre from records; CRM with pipeline and follow-ups | Quotation documents not built |
| 5 Tenders | Register, deadlines, eligibility, checklists, bid approval, award tracking | No external tender-source scraping |
| 6 Procurement | Supplier verification, encrypted dual-controlled bank details, PRs, quote comparison, approvals, POs, landed cost | |
| 7 Finance | Double-entry ledger with database-enforced immutability, multi-currency, invoices, receipts, credit notes, bills, payments, reconciliation, reports | **Accountant sign-off required before live use** |
| 8 Inventory and logistics | Weighted-average stock, goods received, transfers, shipments, customs documents, delivery notes, proof of delivery | Stock valuation not posted to the GL automatically |
| 9 HR and payroll | Employees, contracts, leave, attendance, KPIs, reviews, configurable payroll, self-service | No statutory figures built in; they must come from official sources |
| 10 Communications | Messages, channels, announcements with acknowledgements, tasks, plans and reports, live notifications | WebSocket needs reverse-proxy routing in production |
| 11 JARVIS | Provider layer (Anthropic), typed tools, ActionGateway with live steps, confirm-to-execute, deterministic briefing, usage ledger | Runs on a test provider until the key is supplied |
| 12 Voice | Push-to-talk, spoken replies, voice speed and voice choice, wake-word consent records | STT/TTS providers and the Porcupine engine wait for choices and keys |
| 13 Documents | Branded PDF/Word for invoices, receipts, POs and delivery notes; Word/PDF letterhead; Excel workbooks; version register | Email outbox, calendar and reminders not built (no email provider) |
| Brand | The Director's logo across the app, icons, letterheads and every document | Trademark registration is a separate legal step |
| 14 Production readiness | Checklist, UAT, disaster recovery, deployment and administrator guides | No infrastructure provisioned |
| 15 Installable app | Manifest, icons, shell-only service worker | Native apps not started |

## Questions and needs for the Director

**Keys and providers (secrets go into the server's secret manager, never into chat or email):**

1. **Anthropic API key** for JARVIS. Which model tier: Sonnet (default) or Opus?
2. **Speech-to-text and text-to-speech providers.** Shall I shortlist two or
   three CINEMATIC voices for an audition? The voice must not imitate any
   actor.
3. **Picovoice Porcupine AccessKey**, and the wake phrase to train
   (for example "Hey JARVIS" or "AVEN").
4. **Email provider** (for example Microsoft 365, Google Workspace or an SMTP
   service). It is needed for invitations, reset links, reminders and sending
   documents to customers.

**Company and legal:**

5. **Legal company name, registration status and number**, and the head-office
   address and phone number to print on letterheads and invoices.
6. **TPIN / VAT registration number**, if registered. It is printed only
   once you confirm it.
7. A **trademark check** for the logo and the "JARVIS" assistant name.

**Finance and HR (professional sign-off):**

8. **Accountant** to review the chart of accounts, tax codes and invoice
   layout (MRA requirements).
9. **Payroll rules:** PAYE bands, pension and any other statutory deductions,
   from official sources, signed off by a professional.
10. **Exchange-rate source** (for example the Reserve Bank of Malawi rates) and
    how often rates are entered.
11. **Stock valuation posting to the general ledger:** automatic at each
    movement, or a month-end journal?

**Controls:**

12. **Second approver.** Self-approval is blocked, so anything you raise
    yourself needs another approver. Who should that be? For example, a
    designated Finance manager for amounts below a limit.
13. **Retention periods** for messages, tasks, reports and audit records (the
    proposed defaults are in the communications policy).
14. **Who else should use JARVIS** (it is enabled only for you)?

**Hosting and launch:**

15. **Hosting provider and region:** AWS Cape Town, Azure Johannesburg or
    Google Cloud Johannesburg.
16. **Domain name** for the system (for example `app.<your-domain>`).
17. **Error-tracking and uptime services**, or should I propose them with the
    hosting?
18. **Which documents come next:** quotations, customer statements, contracts,
    tender packs?

**Reviews and merges:**

19. Review and merge **PR #1** (Stages 0–1), **PR #2** (Stage 2) and **PR #3**
    (Stages 3–15), in that order.
