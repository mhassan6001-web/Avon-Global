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

## Points noted while recording

1. **Registration.** The Director states the company is registered. The
   system requires a registration number before the status can show
   "registered", so documents will keep showing "registration pending" until
   the number is entered. No number has been invented.
2. **Legal name.** Recorded as "AVEN GLOBAL". If the registered name carries a
   suffix (for example "Limited"), the Director will enter the exact name.
3. **Sole approver.** With the Director as the only approver:
   - the Director can approve staff requests
   - restricted requests **raised by the Director** stay blocked until a
     second approver is appointed
