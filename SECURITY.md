# Security

## Current position (Stage 1)

**There is no authentication yet.** That is Stage 2. Until then:

- The API exposes only health endpoints. These reveal service name, version,
  environment and dependency up/down state. They expose no hostnames,
  credentials or error internals.
- No business data is stored. The one table (`organisation_profile`) has no
  API and no rows.
- The system must not be deployed anywhere reachable from the internet
  before Stage 2 is approved.

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

## Planned (Stage 2 onward)

Login and logout, Argon2id password hashing, password reset, server-side
sessions with secure cookies, two-factor authentication (TOTP), backend-enforced
roles and individual permissions, account suspension, login history, an
append-only audit log, rate limiting, secure file access, a ban on self-approval
of restricted transactions, and restricted access to payroll, financial data and
supplier bank details.

Each later stage adds its own threat review to this file.

## Design reference

The full security model, including the AI and voice threat model, is in
`docs/security/SECURITY_MODEL.md`.

## Reporting

Report suspected vulnerabilities privately to the Director. Do not open public
issues.
