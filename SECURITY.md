# Security

## Current position (Stages 3–15 built, not deployed)

All business modules, JARVIS, voice and documents are built and tested in CI.
**Before any internet-facing deployment** the items in
`docs/operations/PRODUCTION_CHECKLIST.md` are required, including:

- production object storage
- secrets in a secret manager
- HTTPS and WebSocket routing
- backups with restore tests
- monitoring
- an independent penetration test

## Controls already in place

| Area | Control |
|------|---------|
| Configuration | Validated at startup. Production refuses local DB/Redis hosts, the dev password, non-HTTPS or local CORS origins, non-JSON logs and DEBUG level. |
| Secrets | Read only from the environment. `.env` is git-ignored and not copied into images. |
| Logging | Fields named like password/secret/token/authorization/api_key/cookie are redacted. Incoming request IDs are validated, so they cannot inject into logs. |
| Errors | One envelope. Validation errors drop the submitted `input`, so values such as bank numbers are never echoed. Exception details only appear in development/test. |
| HTTP headers | API: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store`. Web: the same, plus `poweredByHeader` disabled. |
| CORS | Explicit origin allow-list. The web app uses a same-origin proxy, so the browser never calls the API host directly. |
| API docs | `/docs` and the OpenAPI schema are disabled in production. |
| Database | `statement_timeout` per connection, pool pre-ping, explicit transactions. CHECK constraints restrict registration status and currencies, and a "registered" status requires a registration number. |
| Containers | Run as a non-root user. Development ports bind to 127.0.0.1 only. |
| Supply chain | CI runs `bandit` and `pip-audit`. Exact dependency pins (lock files) are required before the first production deployment. |

## Identity and access controls (Stage 2)

| Area | Control |
|------|---------|
| Passwords | Argon2id (argon2-cffi), rehash on parameter change. 12-character minimum. Common-password and personal-information checks. |
| Sessions | 256-bit random token in an HttpOnly, SameSite=Lax cookie (Secure outside development). Only the SHA-256 is stored. Idle 30 minutes, absolute 12 hours. Revoked on logout, suspension, password change or reset. |
| CSRF | Per-session token. `X-CSRF-Token` header required on every state-changing request. |
| 2FA | TOTP (RFC 6238 vectors tested), replay protection, 10 hashed single-use recovery codes. Secrets encrypted with Fernet (`FIELD_ENCRYPTION_KEYS`, rotatable). Mandatory for Director, Finance and HR/Admin. |
| Step-up | Fresh 2FA (or password) within 5 minutes for every administrative change and organisation edit |
| Links | Invitation (72 h) and reset (60 min) links: single use, hash only, issued by the Director |
| Authorisation | Department-scoped roles. Individual overrides (deny wins; Director-only permissions not grantable). `require()` on every route, enforced by the coverage test. |
| Lockout | 5 failed attempts per account per 15 minutes locks it for 15 minutes and raises a security alert. 20 per IP per 15 minutes. **Fails closed** if Redis is unavailable. |
| Enumeration | Identical responses for unknown emails and wrong passwords, with dummy hashing for timing |
| Audit | Append-only table (UPDATE, DELETE and TRUNCATE blocked by triggers), SHA-256 hash chain with verification and an alert on failure |
| Files | Content sniffing against an allow-list, size limit, private storage, permission check at every download, owner-bound 60-second signed URLs, audited |
| Separation of duties | Approval requests can't be decided by their requester (service plus database CHECK constraint) |

## Business, AI, voice and document controls (Stages 3–15)

| Area | Control |
|------|---------|
| Supplier bank details | Encrypted at rest (Fernet), masked in every response. Changes need a Director decision with step-up; nobody approves their own. |
| Finance | Database triggers make posted journals, issued invoices and bills, receipts and exchange rates immutable. Posting enforces balance. Numbering is gap-free (row-locked counters). Corrections only by reversal or credit note. No built-in tax rate. |
| Inventory and logistics | Stock movements and shipment events are append-only. Stock can never go negative (row locks). |
| Payroll | Payroll and compensation are visible only with payroll permissions. Approved runs and payslips are frozen. Staff see only their own payslips. The Director approves payroll; the preparer cannot. |
| Communications | A conversation is readable only by its members (not even the Director otherwise). Messages and reports are append-only. No hidden monitoring (`docs/policies/COMMUNICATIONS_POLICY.md`). The WebSocket authenticates by session cookie, checks Origin, and carries ids only. |
| JARVIS | No SQL. Typed tools wrap permission-checked module functions. The model is told only about the tools the user may use, and results contain only what the user may see. Every call is audited. Changes are only *prepared*: they run after on-screen confirmation, with permissions and rules re-checked. No tool exists for payments, bank changes, tender submission or approvals (an import-time guard enforces this). The test provider is refused in production. |
| Voice | The microphone opens only on push-to-talk and closes on send, stop or tab hide. Audio is transcribed in memory and never stored. A transcript runs through the same gateway as typed text. The wake word is off by default and requires recorded consent (append-only, audited). The Porcupine key is released only to consenting users. Voice never authorises anything. |
| Documents | Built from stored records only, with a permission check per record type. The legal name and registration appear only as configured. Drafts and demo data are labelled. The system never applies a signature or stamp. Every download is audited and registered with a SHA-256. Spreadsheet text can never become a formula. |
| Installable app | The service worker caches only static assets. `/api` data is never cached on the device. |
| Company identity (Stage 16) | Only the Director edits it, with step-up, and every change is audited. TPIN, VAT number, address, phone and email print only when approved; the database refuses an approval without a value. |
| Quotations (Stage 16) | Permission-checked; numbers assigned only at issue; issued quotations and their lines are frozen by database triggers; staff quotations above the configured limit need the Director's approval. |
| Sole approver (Stage 16) | Self-approval stays forbidden in the service and the database. Requests that only their requester could decide are reported as blocked. Fixed controls cannot be switched off through the rules API. |

## Design reference

The full security model, including the AI and voice threat model, is in
`docs/security/SECURITY_MODEL.md`.

## Reporting

Report suspected vulnerabilities privately to the Director. Do not open public
issues.
