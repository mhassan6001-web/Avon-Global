# Director's decisions register

_Recorded 2026-11-12 from the Director's answers to the Stage 3–15 questions.
Earlier decisions are in `PROJECT_STATUS.md`. Nothing here has been purchased,
registered or deployed._

## A. Confirmed decisions

| # | Area | Decision |
|---|------|----------|
| 1 | AI provider | Anthropic. **Sonnet** by default for everyday JARVIS work. **Opus** for complex financial analysis, strategy and hard multi-step tasks where justified. Models are configuration, not code. Keys are stored as server secrets only, never in chat or source. |
| 2 | Speech | STT and TTS providers stay replaceable. The Director chooses the voice after listening to samples. |
| 3 | Wake word | Picovoice Porcupine, optional, with push-to-talk as the fallback and a clear listening indicator. |
| 4 | Email and productivity | Microsoft 365 is the preferred ecosystem (email, Outlook, calendar, Word/Excel, document storage). |
| 5 | Company | Name: AVEN GLOBAL. Headquarters: Lilongwe, Malawi. Address as supplied: Riverside Hotel, Paul Kagame Road, Chilambula Road. Company fields stay editable. |
| 6 | Tax numbers | TPIN and VAT fields exist but are **hidden from all printed documents** until the Director supplies and approves them. |
| 9 | Payroll | PAYE, pension, thresholds and deductions are configurable and date-effective, and never hardcoded. |
| 10 | Exchange rates | Reserve Bank of Malawi is the preferred reference. Record source, currency, rate and retrieval date. Manual entry is allowed with an audit trail. Historical rates never change. |
| 11 | Inventory accounting | **Perpetual**: stock movements post accounting entries in real time. Monthly valuation and reconciliation. |
| 12 | Approvals | Nobody approves their own restricted request. Restricted transactions that need dual approval stay **blocked until a second approver is formally appointed**. Limits and permissions are configurable. |
| 14 | JARVIS access | Director only. The Director can enable individual staff later. JARVIS never exceeds the user's role. |
| 18 | Document order | (1) letterhead and quotations, (2) invoices and receipts, (3) customer statements, (4) purchase orders and supplier quotations, (5) contracts and service agreements, (6) tender packs. PDF, Word and Excel where appropriate. |

## B. Proposed decisions awaiting the Director's approval

| # | Area | Proposal | What is needed before approval |
|---|------|----------|-------------------------------|
| 2 | Voice | 2–3 providers with deep, original male voices | Shortlist with samples, latency, cost and commercial rights |
| 3 | Wake phrase | "Hey JARVIS" | Compatibility test; check that Porcupine permits and can train this phrase under the paid licence |
| 13 | Retention | Financial records, audit logs and supporting reports: 7 years minimum. Ordinary internal messages: 2 years. HR records: per employment and privacy law. No deletion under legal hold. | Legal confirmation for Malawi |
| 15 | Hosting | Microsoft Azure, South Africa North (Johannesburg) | Pricing, service availability, database, backup and security comparison, with expected monthly cost |
| 16 | Domain | `avenglobal.com`, alternative `avenglobal.mw` | Availability and price check |
| 17 | Monitoring | Error tracking, uptime, server, database and performance monitoring, with alerts to the Director | Cost comparison and recommendation |

## C. Information the Director still needs to supply

See `docs/OUTSTANDING_INFORMATION.md`.

## D. Items requiring professional verification

| Item | Who |
|------|-----|
| Chart of accounts, tax codes, VAT treatment, invoice and quotation layouts, financial statements, bank reconciliation, accounting controls | Qualified Malawi accountant (not yet appointed) |
| PAYE and pension calculations before any live payroll | Accountant, from official MRA and pension sources |
| Inventory valuation method (weighted average or FIFO) before live posting | Accountant |
| Accounting treatment of exchange differences | Accountant |
| Retention periods and deletion procedures | Legal adviser (Malawi tax, employment and privacy law) |
| Trademark availability: AVEN GLOBAL name and logo, and JARVIS for commercial use | Preliminary search by the project; a trademark attorney or the Malawi registry for a formal opinion |

Until these are signed off, the system's tax, payroll and accounting settings
are **not legally approved**, and the app says so on the finance screens.

## Confirmed by the Director on 2026-11-12 (second message)

1. **Registration number:** `BRN-M7S4Y5AW`. Status: registered. The Director
   enters it in Admin → Organisation at first run; it then prints on documents.
2. **Legal name:** AVEN GLOBAL (no suffix).
3. **Approver:** the Director is the only approver. No second approver will be
   appointed for now.

### What "sole approver" means in the system

- The Director approves every restricted request that staff raise.
- The rule that nobody approves their own restricted financial request stays
  in force (master instructions §8). So a payment, supplier bank change,
  credit note, manual journal, payroll run, purchase order or tender
  submission that the **Director raises personally** cannot be approved by the
  Director. The Approvals screen marks it "Blocked: no second authorised
  approver".
- The working pattern is therefore: **staff prepare, the Director approves.**
- Quotations are offers, not money movements. A user who holds the quotation
  approval permission (the Director) issues their own quotations directly.
  Staff quotations go to the Director above the configured limit.
- If the Director later wants to approve their own restricted requests, that
  is a change to the master rule and needs an explicit written decision.

## Confirmed by the Director on 2026-11-12 (third message)

- **Pull requests:** the Director asked for PRs #1, #2 and #3 to be merged on
  his behalf. Merged into `main` on 2026-11-12.
- **Business telephone (for now):** +265 999 667 007. To be entered in
  Admin → Organisation; it prints once ticked "Approved to print".
- **Voice audition:** trial accounts approved (ElevenLabs, Azure Speech,
  Cartesia). No payment.
- **JARVIS name:** internal use only.
- **Trademark:** formal Malawi search for AVEN GLOBAL approved in principle;
  the fee and practitioner still need the Director's go-ahead.
- **Monitoring:** Sentry plus Better Stack approved in principle. Nothing
  purchased.
- **Hosting:** the Director asked for a free option first. See
  `docs/research/HOSTING_FREE_OPTIONS.md`.
- **Anthropic API key:** supplied by the Director. It is **not stored in this
  repository, in documents or in chat records by the project**. It belongs
  only in the server's secret store (or a local `.env` file that git ignores).
- **Remaining stages:** approved to proceed. TPIN and VAT number to follow.
