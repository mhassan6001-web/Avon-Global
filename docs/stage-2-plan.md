# Stage 2 plan: identity and security

- Status: **Plan awaiting Director approval.** No Stage 2 code has been
  written.
- Builds on: Stage 1 (approved 2026-11-12), `docs/security/SECURITY_MODEL.md`.

## 1. Scope

Login and logout, Argon2id password hashing, password reset, sessions,
two-factor authentication (TOTP), user administration, roles and individual
permissions, activation and suspension, login history, an append-only audit
log, backend permission enforcement, rate limiting and secure file access.
It also creates the six initial roles and development-only test accounts.

**Not in scope:** any business module data (CRM, finance, payroll and so on),
email delivery (Stage 13) and SSO.

## 2. Design

### Authentication and sessions

- **Passwords:**
  - Argon2id (`argon2-cffi`, OWASP parameters), with rehash on login when
    the parameters change.
  - Minimum 12 characters, checked against a bundled common-password list.
  - No forced periodic rotation.
- **Sessions:**
  - An opaque 256-bit random token in an `HttpOnly; Secure; SameSite=Lax`
    cookie on the web origin (the same-origin proxy from ADR-0001).
  - Only a SHA-256 hash of the token is stored, in `auth_sessions`.
  - Idle timeout 30 minutes and absolute lifetime 12 hours, both
    configurable.
  - Users can see and revoke their sessions. Suspending a user revokes all
    of theirs.
- **CSRF:** SameSite=Lax plus a per-session token in an `X-CSRF-Token` header
  on every state-changing request.
- **Two-factor authentication:**
  - TOTP (RFC 6238, `pyotp`) with 10 single-use recovery codes, stored
    hashed.
  - TOTP secrets are encrypted at rest with a key from environment secrets
    (`cryptography` Fernet).
  - 2FA is mandatory for Director, Finance and HR/Admin. Other roles may
    enrol.
- **Step-up:** a fresh 2FA check within the last 5 minutes for user, role and
  permission administration, and for every action marked `sensitive`.
- **Activation:**
  - The Director (or HR/Admin, for non-Director staff) creates an account.
  - The system produces a single-use invitation link, valid for 72 hours.
  - The user sets a password and enrols 2FA where it is mandatory.
- **Password reset:**
  - Self-service is built behind an `EmailSender` interface with a
    development "outbox" (shown in a dev-only page) until real email arrives
    in Stage 13.
  - Until then, production resets are **administrator-issued one-time links**.
    See Decision 2.
- **Rate limiting:**
  - Redis sliding window: login 5 per 15 minutes per account and 20 per
    15 minutes per IP; 2FA 5 per 5 minutes; reset 3 per hour.
  - Plus a general per-user API limit.
  - Progressive lockout, with a recorded audit event.
- **First Director in production:** a one-time CLI command
  (`python -m app.cli create-director`). It refuses to run if a Director
  already exists.

### Authorisation

- **Permission catalogue** in code: `module.resource.action` strings for
  **every planned module**, so Stage 4 onward plug into an existing catalogue.
  Sensitive permissions are flagged, for example:
  - `finance.ledger.view`
  - `hr.payroll.view`
  - `procurement.supplier_bank.view`
  - `procurement.supplier_bank.change`
- **Tables:** `roles`, `permissions`, `role_permissions`, `user_roles` and
  `user_permission_overrides` (explicit **grant** or **deny**; deny wins).
- **Enforcement:** a FastAPI dependency, `require("module.resource.action")`.
  A route-coverage test fails the build if any `/api/v1` route other than
  health and public auth lacks a permission requirement.
- **Separation of duties:** a reusable `ensure_not_self_approval()` guard and
  an approval-request primitive. Business modules call these from Stage 4
  onward. Stage 2 tests them directly.
- **Field-level restriction:** a serialiser helper masks restricted fields
  (bank account numbers, salary) unless the caller holds the matching `view`
  permission. It is tested in Stage 2 and applied to real data as modules
  arrive.

### Proposed initial role matrix (Decision 1)

| Area | Director | Business Dev. | Procurement | Finance | Logistics | HR/Admin |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| Director dashboard | ✓ | — | — | — | — | — |
| CRM, quotations | ✓ | ✓ edit | view | view | — | — |
| Tenders | ✓ approve | ✓ edit | ✓ edit | view | — | — |
| Suppliers (no bank details) | ✓ | view | ✓ edit | view | view | — |
| **Supplier bank details** | ✓ view, approve change | — | **request change only** | ✓ view | — | — |
| Purchase requests and orders | ✓ approve | — | ✓ create | view | view | — |
| **Finance ledger, invoices, payments** | ✓ | own invoices view | — | ✓ | — | — |
| Inventory and logistics | ✓ | view | view | view | ✓ edit | — |
| Employees (non-salary) | ✓ | — | — | — | — | ✓ |
| **Payroll and salaries** | ✓ | — | — | totals only | — | ✓ prepare |
| Communications and tasks | ✓ | ✓ own | ✓ own | ✓ own | ✓ own | ✓ own |
| User and role admin | ✓ | — | — | — | — | create/suspend staff, not roles |
| Audit log | ✓ | — | — | — | — | — |

A supplier bank change always needs the requester plus a **different**
approver (the Director), with step-up authentication.

### Audit and history

- **`audit_events`** records actor, action, target, before and after values
  (sensitive fields redacted), IP, user agent, request ID and outcome.
  - It is **append-only**: database triggers block UPDATE and DELETE, and the
    application's database role has no such privileges.
  - It carries a **hash chain**, where each row stores the hash of the
    previous row, so tampering is detectable. A verification command checks
    the chain.
- **`login_events`** records successes, failures, lockouts, 2FA results,
  IP, user agent and time.
- **Viewers:** the Director sees the audit log and everyone's login history.
  Each user sees their own login history.

### Secure file access

- A `StorageBackend` interface. Development uses a local Docker volume.
  Production uses S3-compatible private object storage (Stage 14).
- `stored_files` records the owner, module, permission required, SHA-256,
  size and MIME type, checked by content sniffing against an allow-list.
- Size limit 25 MB, configurable.
- **Downloads only through the API** after a permission check, or via signed
  URLs that expire in 60 s. There are no public buckets. Every download is
  audited.
- Antivirus scanning is noted for Stage 14.

### Organisation profile

The Stage 1 `organisation_profile` table gets an API. Everyone signed in can
read it. **Only the Director can edit it**, with step-up authentication and
an audit entry.

### Frontend

- **Pages:**
  - sign in and 2FA challenge
  - invitation acceptance, password set and 2FA enrolment (QR code)
  - forgot and reset password
  - account security: change password, 2FA, recovery codes, active sessions
  - Admin › Users: create, invite, suspend, reactivate, roles, overrides
  - Admin › Roles (read-only matrix view)
  - Admin › Audit log and login history, with filters
- **Protection:** Next.js middleware redirects to sign-in when there is no
  session. The server is still the authority, because every API call is
  checked.
- The header profile area shows the real user and role, and sign-out.

### Development-only test accounts

- A `python -m app.cli seed-dev-users` command **refuses unless
  `APP_ENV=development`**.
- It creates one account per role, all clearly marked:
  - emails `<role>@dev.aven.invalid` (`.invalid` cannot receive mail)
  - display name prefixed "DEV-ONLY"
  - random passwords printed once
  - TOTP secrets printed once
- The UI shows a "DEVELOPMENT ACCOUNT" banner on these accounts.

## 3. Database changes (Alembic migration 0002, reversible)

New tables:

- `users`
- `auth_sessions`
- `user_mfa` (encrypted secret, recovery-code hashes)
- `invitations`
- `password_reset_tokens`
- `roles`
- `permissions`
- `role_permissions`
- `user_roles`
- `user_permission_overrides`
- `login_events`
- `audit_events` (with triggers)
- `stored_files`

The migration seeds the six roles and the permission catalogue. **It creates
no users.** No existing data is changed or deleted.

## 4. New dependencies

- **Backend:** `argon2-cffi`, `pyotp`, `cryptography`, `redis`, `segno` (QR
  codes for TOTP enrolment) and `python-multipart` (uploads).
- **Frontend:** none expected.

## 5. Acceptance tests (all must be executed, not just written)

1. **Role × endpoint matrix:** every protected endpoint is called as each of
   the six roles, as an anonymous caller, and as a suspended user. The
   expected outcome is 200/201, 403 or 401 exactly per the matrix.
2. **Route coverage:** the build fails if a route has no permission
   requirement.
3. **Sensitive data:** for each role without the `view` permission, payroll
   and salary, ledger, and supplier-bank fields are masked or refused.
4. **Self-approval** is refused, including for the Director. A supplier bank
   change needs a second, different approver plus step-up.
5. **Passwords:** Argon2id hash format, and no plaintext anywhere in the
   database or logs (log-capture test).
6. **Sessions:**
   - idle and absolute expiry
   - logout invalidates the session server-side
   - suspension revokes all sessions immediately
   - a session token is not usable after a password change
7. **CSRF:** a state-changing request without the token gets 403.
8. **2FA:**
   - enrolment, challenge, recovery-code single use
   - mandatory roles cannot skip enrolment
   - step-up expires after 5 minutes
9. **Rate limits:** thresholds and lockout behave as specified. Failed
   attempts appear in login history.
10. **Reset and invitation tokens:** single use, expiry, hash-only storage,
    and no user enumeration (identical responses for unknown emails).
11. **Audit log:** UPDATE and DELETE are rejected by the database, and the
    hash-chain verification detects a tampered row.
12. **Files:**
    - unauthorised download gets 403
    - signed URLs expire
    - MIME spoofing is rejected
    - the size limit is enforced
    - downloads are audited
13. **Dev seed** refuses outside development.
14. **Migration** `0002` upgrade → downgrade → upgrade on PostgreSQL, plus a
    model/migration drift check.
15. **Frontend:** sign-in, 2FA, logout and admin flows run in a headless
    browser against the real API.
16. **Tooling:** ruff, mypy (full), bandit, pip-audit, eslint, tsc,
    `next build`, and API and web startup.

## 6. Blocking constraint: test execution

Stage 2 is security-critical and **must not be approved on unexecuted
tests**. This build workspace currently **cannot download packages**, so it
can run neither FastAPI, SQLAlchemy and Alembic nor the new security
libraries.

One of these is needed before implementation (Decision 3):

- **A. Recommended:** turn on package installs in the network settings of
  your Claude workspace, then start a new chat in this Project. The new
  setting only applies to new chats. I can then run every test above myself.
- **B.** Create a private GitHub repository and connect it. CI runs the full
  suite on every change, and I report the CI results.
- **C.** You run `make check` on your computer with Docker Desktop and paste
  the output back.

## 7. Decisions for the Director

1. **Role matrix:** approve §2 as proposed, or amend it.
2. **Password reset before email exists (Stage 13):** administrator-issued
   one-time links (recommended), or bring email delivery forward into
   Stage 2.
3. **Test execution route:** A, B or C (§6).
4. **2FA:** mandatory for Director, Finance and HR/Admin (recommended), or
   for all staff.
