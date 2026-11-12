# AVEN GLOBAL master architecture (Stage 0 blueprint)

- Status: **Approved by the Director on 2026-11-12** (Stage 0). The received
  Stage 0 text is incomplete, and any later sections will be reconciled when
  supplied.
- Sources:
  - the Stage 0 specification (`docs/stage-0-specification.md`)
  - the master project instructions
  - the JARVIS design specification
  - the Director's stage plan
  - the inspected Stage 1 repository
- **Received text is incomplete.** The Stage 0 specification ends at section
  4 "I. STAFF COMMUNICATIONS" (line 208). Anything specified after that point
  has not been received and is **not** covered here. Staff communications
  below is taken from the master instructions §12 and the Director's Stage 10
  plan.
- Stage 0 was authorised after Stage 1 had already been built and approved.
  This document therefore also **reconciles the existing code against the
  blueprint** (§14).

---

## 1. Product and platforms

AVEN GLOBAL is one centralised, cloud-hosted business operating system for a
Malawi-based international procurement, supplies, sourcing, import/export and
distribution company. "2050" is a visual direction only, never part of the
name.

| Client | Delivery |
|--------|----------|
| Windows and macOS computers | Modern browsers (Chrome, Edge, Safari, Firefox), plus an optional install as a PWA |
| iPhone and Android phones | Responsive web app installed as a **PWA** (Stage 15). Native apps are assessed afterwards. |
| Tablets | Dedicated tablet layouts (768–1199 px) |

**All clients use one backend, one database and one set of business rules.**
No business logic is duplicated on a client.

## 2. System context

```
 Director / staff devices ──HTTPS──► Edge (TLS, WAF, rate limit)
                                         │
                       ┌─────────────────┴──────────────────┐
                       ▼                                    ▼
               Web (Next.js, PWA)  ──/api/v1 proxy──►  API (FastAPI, REST + WebSocket)
                                                            │
     ┌──────────────┬───────────────┬──────────────┬────────┴─────┬───────────────┐
     ▼              ▼               ▼              ▼              ▼               ▼
 PostgreSQL     Redis          Object storage   Workers       AI provider     Speech providers
 (system of     (cache, rate   (S3-compatible,  (Celery +     (Anthropic      (STT/TTS behind
 record)        limits, pub/   private)         beat)         Claude)         interfaces)
                sub, broker)
                                                    │
                       External: email, calendar, web push, permitted tender sources
```

## 3. Logical architecture: modular monolith

One API codebase (ADR-0001, accepted). Each business module is a package under
`backend/app/modules/<module>/` with this fixed internal layout:

```
models.py     SQLAlchemy models (tables prefixed by module)
schemas.py    Pydantic request/response models
service.py    business rules, transactions, permission checks
router.py     HTTP endpoints → services only
events.py     domain events published to the event bus
tools.py      JARVIS tool definitions wrapping service functions (Stage 11+)
tests/        unit + integration tests for the module
```

**Boundary rule:** modules interact through each other's `service.py` and
through domain events. They never read or write another module's tables.

### 3.1 Business modules

These are Stage 0 modules A–I, mapped to delivery stages.

| Module | Package | Key capabilities (Stage 0 + master instructions) | Stage |
|--------|---------|---------------------------------------------------|-------|
| A. Director Command Centre | `director` | Business overview, revenue and expenses, cash position, profitability, outstanding invoices, supplier liabilities, active tenders, pending approvals, staff performance, alerts and business intelligence | 4 (complete as modules arrive) |
| B. JARVIS AI | `jarvis` | Voice and text, business intelligence, daily briefings, reports, task management, authorised actions, business-wide search, staff communication assistance | 11–12 |
| C. CRM and Sales | `crm` | Customers, prospects, contacts, pipeline, quotations, **contracts**, follow-ups, history | 4 |
| D. Tender Management | `tenders` | Opportunities including **government, NGO and UN**, documents, eligibility, deadlines, compliance checklists, **bid costing**, submission tracking, awards and unsuccessful bids | 5 |
| E. Procurement and Suppliers | `procurement` | Suppliers, verification, quotations, purchase requests and orders, approval workflows, tracking, landed cost, **supplier performance** | 6 |
| F. Finance and Accounting | `finance` | Invoices, receipts, payments, expenses, cashbook, debtors, creditors, bank reconciliation, P&L, balance sheet, cash flow, **multi-division profitability**, reporting | 7 |
| G. Inventory and Logistics | `inventory`, `logistics` | Stock, warehouses, movements, purchase receipts, shipments, customs documents, deliveries, reorder alerts, valuation | 8 |
| H. Human Resources | `hr` | Employee records, contracts, attendance, leave, payroll, performance, staff assignments, departments | 9 |
| I. Staff Communications | `comms` | Messaging, channels, announcements, tasks, work plans, end-of-day reports, Director follow-ups | 10 |

**Bold** items come from Stage 0 and were not in the master instructions.
They are now in scope for their stage.

### 3.2 Shared platform services (`app/platform/`)

| Service | Purpose | Stage |
|---------|---------|-------|
| Identity and sessions | Login, 2FA, sessions, invitations | 2 |
| Authorisation | Permission catalogue, role and override evaluation, field masking | 2 |
| Audit | Append-only, hash-chained audit events | 2 |
| Approvals | Approval requests, separation of duties, step-up | 2 (primitive), used from 4 |
| Organisation | Legal name, registration, divisions, currencies | 1 (table), 2 (API) |
| Files | Upload validation, private object storage, signed access | 2 |
| Numbering | Gapless per-type, per-year document numbers allocated in a transaction | 4/7 |
| Currency and FX | Currencies (MWK functional; USD, ZAR, ZMW), dated exchange rates with source | 4/7 |
| Notifications | In-app, WebSocket push, web push (PWA), email (Stage 13) | 3/10/13 |
| Events | In-process domain-event bus, plus Redis pub/sub fan-out | 4 |
| Search | PostgreSQL full-text search, permission-filtered | 4 |
| Documents | PDF, Word and Excel rendering from validated records, versioned | 7/13 |
| Jobs | Celery tasks and schedules (reminders, alerts, renders, imports) | 4/5 |
| AI gateway | Provider abstraction, tool registry, ActionGateway, usage ledger | 11 |
| Speech | STT/TTS interfaces, wake-word configuration | 12 |

## 4. Data architecture

- **PostgreSQL 16** is the single system of record. Alembic migrations are
  linear, reversible where data allows, and reviewed. Destructive migrations
  need Director approval and a verified backup.
- **Conventions:**
  - UUID primary keys
  - `created_at`, `updated_at` and `created_by` on every business table
  - UTC storage, displayed in Africa/Blantyre by default
  - module-prefixed table names (`crm_*`, `fin_*`, `proc_*` and so on)
  - named constraints (naming convention in place since Stage 1)
- **Money** is `NUMERIC(20,4)` with an ISO currency code, never floating
  point. Each amount records its transaction currency and an MWK functional
  amount at a recorded rate.
- **Immutability:**
  - Posted financial records are never updated or deleted. Corrections use
    reversals and credit notes.
  - Master data is archived, not deleted.
  - The audit log is append-only.
- **Data integrity in the database:** foreign keys, CHECK constraints (for
  example currency codes and status values), unique document numbers, and a
  rule that journal lines balance per entry, enforced by a deferred
  constraint trigger.
- **Development data:** clearly labelled demo data only, created by
  development-only commands. Never in production.

## 5. Finance architecture (summary)

- `fin_journal_entries` and `fin_journal_lines` (debit/credit, account,
  division, contract or project reference, currency, functional amount).
- The posting service is the **only** path that writes journals.
- Financial periods can be opened, closed and locked.
- Source documents (invoice, receipt, bill, payment, credit note) post through
  the posting service.
- Revenue invoiced and cash collected are always reported separately.
- Tax is configuration (`fin_tax_codes`, with rate history), never a constant.
  **Statutory configuration requires sign-off by a qualified Malawi accountant
  before live use**, recorded in the system.
- Reports (P&L, balance sheet, cash flow, aged debtors and creditors,
  division and contract profitability) are generated from posted journals
  only. Estimates are labelled as estimates.

## 6. Real-time communication

FastAPI WebSocket endpoint `/api/v1/ws`:

- authenticated by the session cookie, with channel subscriptions
  permission-checked
- Redis pub/sub fans messages out across API instances
- carries messages, notifications, task updates, approval updates, JARVIS
  state and live dashboard refresh signals
- the client reconnects with backoff and re-syncs missed items over REST
  (the database is the source of truth)

## 7. Background processing

**Celery with a Redis broker, plus Celery beat** for schedules. This is kept
as the Director specified, and it suits mixed CPU and I/O work (document
rendering, imports).

- Tasks are idempotent, with idempotency keys.
- Results that matter are persisted to PostgreSQL, not only to the result
  backend.
- Schedules cover tender deadline alerts, invoice due reminders, overdue
  tasks, FX-rate checks and backup verification.

*Alternatives considered:* Dramatiq or arq would be simpler. They are not
adopted because there is no requirement driving a change.

## 8. Storage and documents

- **S3-compatible private object storage** in production. Development uses a
  local volume behind the same interface.
- Server-side encryption, no public buckets, signed URLs of 60 seconds or
  less, and audited downloads.
- **Documents:**
  - rendered by workers: PDF via HTML templates (for example WeasyPrint),
    Excel with openpyxl, Word with python-docx
  - branded templates
  - unique numbering and version history
  - no fabricated signatures or approvals

## 9. AI and voice

See `docs/architecture/AI_ARCHITECTURE.md` and `VOICE_AND_SOUND.md`, both
approved. Confirmed settings: voice **CINEMATIC**, activation **WAKE_WORD**,
sound **IMMERSIVE**. Wake-word engine: **Picovoice Porcupine, paid licence**
(Director decision, 2026-11-12). The AccessKey will be supplied by the
Director later and is held only in environment secrets. Until it is supplied,
the wake word is unavailable and push-to-talk works normally.

## 10. Security

See `docs/security/SECURITY_MODEL.md` and `/SECURITY.md`. Key properties:

- backend-enforced permissions
- 2FA and step-up authentication
- separation of duties
- restricted payroll, finance and supplier-bank data
- append-only audit
- encryption in transit and at rest (database, backups, object storage)
- rate limiting
- no hidden surveillance

## 11. Deployment architecture

| Component | Production form |
|-----------|-----------------|
| Web | Next.js standalone container (≥ 2 replicas) |
| API | Uvicorn workers in containers (≥ 2 replicas), behind a load balancer with TLS |
| Workers | Celery worker containers, plus one beat scheduler |
| Database | Managed PostgreSQL 16 with point-in-time recovery, daily encrypted snapshots, and a tested restore |
| Redis | Managed Redis with TLS and auth |
| Storage | Managed S3-compatible bucket with versioning |
| Edge | Managed load balancer and TLS certificates (automatic renewal), with WAF where available |
| Observability | Structured JSON logs (in place), metrics, error reporting, uptime checks, alerting |

- **Environments:** development (Docker Compose, in place), CI (GitHub
  Actions, in place), staging, production.
- **Release process:** build → CI → deploy to staging → run the migration
  step → smoke tests → Director approval → production.
- **Hosting region (decision for Stage 14):** a Southern Africa cloud region
  for latency to Malawi and data proximity. Candidates are AWS (Cape Town),
  Azure (South Africa North) and Google Cloud (Johannesburg). Region
  availability and pricing are to be verified at the time.
- Supabase, Vercel and localhost-as-production are excluded.

## 12. Integrations

All integrations sit behind interfaces, and none is assumed to be connected.

- Email and calendar (Stage 13).
- Web push notifications for the PWA (Stage 15).
- **External tender monitoring:**
  - only permitted sources: official procurement portals, RSS or APIs, and
    sites whose terms allow it
  - every record stores its source URL and last-checked time
  - no fabricated opportunities and no automated bid submission
- AI and speech providers are covered in §9.

## 13. Non-functional targets (proposed)

| Area | Target |
|------|--------|
| API latency | p95 < 300 ms for reads and < 800 ms for writes, excluding AI, documents and imports |
| Availability | 99.5% monthly at launch |
| Recovery | RPO ≤ 15 min (point-in-time recovery), RTO ≤ 4 h. Restore tested quarterly. |
| Accessibility | WCAG 2.2 AA. Reduced motion, high contrast and keyboard access (already in Stage 1). |
| Performance | Largest Contentful Paint < 2.5 s on mid-range Android over 4G. Animations at 60 fps with no long tasks over 50 ms. |
| Security | OWASP ASVS Level 2 as the verification baseline |

## 14. Reconciliation with the existing repository (Stage 1, approved)

| Blueprint element | Repository today |
|-------------------|------------------|
| Next.js, TypeScript, Framer Motion | ✔ Built (Stage 1) |
| FastAPI REST, versioned | ✔ `/api/v1` |
| PostgreSQL, SQLAlchemy, Alembic | ✔ Baseline migration 0001 |
| Configuration, logging, errors, health | ✔ |
| Redis | ✔ Readiness probe. Celery not yet added (§7). |
| WebSockets | ✘ Planned (§6) |
| PWA installability | ✘ Planned (Stage 15) |
| Tablet layouts | ⚠ Responsive breakpoints exist at 900 px and 1100 px. Dedicated tablet layouts are still to do. |
| S3 object storage | ✘ Planned (Stage 2 interface, Stage 14 production) |
| Module package layout (§3) | ⚠ `app/modules/organisation` exists. The `app/platform/` folder will be introduced in Stage 2. |
| **Visual design versus reference images** | ⚠ Stage 1 used the images as inspiration only. The new fidelity instruction makes them the **primary specification**. The deviations are recorded in `REFERENCE_IMAGE_SPECIFICATION.md` §5 and will be corrected in Stage 3. |

Nothing in the existing code conflicts with this blueprint, so no rework is
needed before Stage 2.

## 15. Open decisions

1. **The rest of the Stage 0 specification** (text after "I. STAFF
   COMMUNICATIONS").
2. The Stage 2 plan decisions: role matrix, password reset before email,
   test-execution route, and 2FA policy.
3. The reference-design conflicts listed in `REFERENCE_IMAGE_SPECIFICATION.md`
   §6.
4. Hosting provider and region, error-reporting service, and email provider
   (by Stage 13/14).
5. STT/TTS provider shortlist for the CINEMATIC voice (by Stage 12).
