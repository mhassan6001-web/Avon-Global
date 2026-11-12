# Stage 2 report: authentication and security

- Date: 2026-11-12
- Status: **Built and verified in CI. Awaiting Director approval.**
- Branch: `stage-2-identity-security`, PR #2, based on PR #1
  (`stage-1-baseline`).
- Plan: `docs/stage-2-plan.md` (approved with Director decisions).

## 1. Executed results (GitHub Actions, latest commit)

| Job | Check | Result |
|-----|-------|--------|
| backend | ruff lint and format | Pass |
| backend | mypy (strict) | "no issues found in 60 source files" |
| backend | bandit, pip-audit | Pass |
| backend | pytest | **123 passed**, 0 failed, 0 warnings. **46 integration tests** on real PostgreSQL 16 and Redis 7. |
| backend | Alembic | downgrade base → upgrade head → `alembic check` passed. Head `0002`. No model drift. |
| backend | API startup | live=200, ready=200 (database, migrations and Redis OK) |
| frontend | Prettier, ESLint, tsc | Pass |
| frontend | Unit tests | 21/21 |
| frontend | `next build` | Compiled, 25 routes generated |
| e2e | Playwright (Chromium) against the running API and built web app | **6/6 passed** |

## 2. Acceptance tests against the plan (§5)

| # | Plan item | Test(s) | Result |
|---|-----------|---------|--------|
| 1 | Role × endpoint matrix, plus anonymous and suspended | `test_role_matrix` (6 roles), `test_anonymous_and_suspended_are_rejected` | ✔ |
| 2 | Route coverage | `test_every_route_is_guarded`, `test_public_and_partial_routes_are_exactly_the_allow_lists`, `test_router_list_covers_every_published_endpoint`, `test_admin_routes_require_permissions` | ✔ |
| 3 | Sensitive data restriction | `test_sensitive_data_matrix` (payroll: Director and HR; ledger: Director and Finance; supplier bank: Director only; audit: Director only), `test_staff_roles_never_hold_director_only_or_cross_department` | ✔ |
| 4 | Self-approval blocked, including for the Director | `test_separation_of_duties` (service **and** database constraint) | ✔ |
| 5 | Argon2id, no plaintext in the database or logs | `test_login_success_sets_secure_session`, `test_no_plaintext_password_in_logs` | ✔ |
| 6 | Session expiry and revocation | `test_idle_and_absolute_expiry`, `test_logout_invalidates_server_side`, `test_suspension_revokes_sessions_immediately`, `test_password_change_revokes_other_sessions` | ✔ |
| 7 | CSRF | `test_csrf_required_for_state_changes` | ✔ |
| 8 | 2FA enrolment, verification, replay, recovery codes, mandatory roles, step-up | `test_mandatory_mfa_enrolment`, `test_mfa_login_replay_and_recovery_code`, `test_recovery_codes_single_use`, `test_step_up_required_for_admin_changes`, plus RFC 6238 vectors | ✔ |
| 9 | Rate limits and lockout, with login history and alert | `test_lockout_after_repeated_failures`, `test_per_ip_rate_limit` | ✔ |
| 10 | Links: single use, expiry, hash-only, no user enumeration | `test_invitation_flow_and_hash_only_storage`, `test_reset_link_revokes_sessions_and_expires`, `test_wrong_password_and_unknown_email_are_indistinguishable` | ✔ |
| 11 | Audit log append-only and tamper-evident | `test_audit_log_append_only_and_tamper_evident` (UPDATE, DELETE and TRUNCATE rejected; tampering detected; alert raised) | ✔ |
| 12 | Files: permission, signed-URL expiry and ownership, MIME spoofing, size limit, audited | `test_files_access_follows_permissions`, `test_file_validation`, `test_expired_signed_url` | ✔ |
| 13 | Development seed refuses outside development | `test_dev_users_only_exist_in_development` | ✔ |
| 14 | Migration round-trip and drift | CI Alembic step and `test_migrations.py` | ✔ |
| 15 | Browser flows | e2e: redirect, generic error, department scoping, Director 2FA plus invitation flow, sign-out, phone viewport | ✔ |
| 16 | Tooling | See §1 | ✔ |

Also covered:

- **Individual overrides:** grant, deny, revoke, and the rule that
  Director-only permissions can never be granted
  (`test_overrides_extend_and_restrict_individuals`)
- **The Director role can't be assigned or created through the API**
  (`test_director_accounts_cannot_be_created_or_assigned_via_api`)
- **Organisation profile rules** (`test_organisation_profile_rules`)

## 3. Real bugs found by CI during the stage (fixed)

- Client addresses that are not IPs (proxies, test clients) caused a database
  error. They are now validated, and stored as null when invalid.
- One login-history outcome label exceeded its 32-character column. Labels
  were shortened.
- A FastAPI version change wraps included routers, which hid routes from the
  coverage test. It now uses an explicit router list, cross-checked against
  the published API spec.

## 4. Scope notes and limits

- **Business modules have no endpoints yet**, so "every protected module" is
  tested two ways:
  - at the permission-catalogue level for all 11 planned modules
  - at the endpoint level for every endpoint that exists
  
  The matrix and route-coverage tests grow automatically as module routers
  are added.
- **Password reset by email** is deferred to Stage 13 (Director decision).
  Until then, the Director issues one-time links.
- **File storage** uses a local volume in development and CI. Production
  object storage is Stage 14.
- **Visual design:** the new screens use the Stage 1 component language. They
  will be restyled to the reference images in Stage 3 (C1–C9).
- **Not run by Claude:** `make up` on a desktop (no Docker daemon in the
  build workspace). CI covers the same services.

## 5. How to try it

```bash
make up
make seed-dev-users        # prints DEV-ONLY accounts, passwords and TOTP secrets once
```

Add a TOTP secret to an authenticator app for the Director, Finance and
HR/Admin accounts.
