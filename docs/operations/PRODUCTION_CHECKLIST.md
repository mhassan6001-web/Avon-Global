# Production readiness checklist (Stage 14)

Status: **not production-ready.** The application builds and passes CI, but
building is not the same as being ready. Nothing may be deployed without
Director approval. Each item needs evidence: a link, a screenshot or a test
run ID.

Legend: ☐ open · ◐ partly done · ☑ done with evidence

## A. Decisions and inputs from the Director

| # | Item | Status |
|---|------|--------|
| A1 | Hosting provider and region (`DEPLOYMENT_ARCHITECTURE.md` §3) | ☐ |
| A2 | Legal company name, registration status and number in the organisation profile | ☐ |
| A3 | Anthropic API key and model choice for JARVIS | ☐ |
| A4 | Speech-to-text and text-to-speech providers, plus the voice audition (VO-01) | ☐ |
| A5 | Picovoice Porcupine AccessKey and trained wake phrase | ☐ |
| A6 | Email provider (invitations, reset links and notifications are currently Director-issued links) | ☐ |
| A7 | Second approver for restricted transactions (self-approval is blocked) | ☐ |
| A8 | Retention periods (`docs/policies/COMMUNICATIONS_POLICY.md`) | ☐ |

## B. Accountant and statutory review (before any live posting)

| # | Item | Status |
|---|------|--------|
| B1 | Chart of accounts reviewed by a qualified Malawi accountant | ☐ |
| B2 | Tax codes and rates (all configuration, none built in) | ☐ |
| B3 | Payroll components, PAYE bands and pension, entered from official sources | ☐ |
| B4 | Exchange-rate source and the rule for using it | ☐ |
| B5 | Inventory valuation posting to the general ledger (not yet automated) | ☐ |
| B6 | Invoice and receipt layout acceptable to the Malawi Revenue Authority | ☐ |

## C. Infrastructure

| # | Item | Status |
|---|------|--------|
| C1 | HTTPS everywhere, HSTS, certificates managed by the provider | ☐ |
| C2 | Managed PostgreSQL 16: HA, PITR, encryption at rest, private network | ☐ |
| C3 | Managed Redis with TLS and auth | ☐ |
| C4 | Private object storage for uploaded files (the app currently uses `STORAGE_DIR`) | ☐ |
| C5 | Reverse proxy routes `/api/v1/ws` WebSocket upgrades to the API | ☐ |
| C6 | Secrets in the provider secret manager; production config guard passes | ◐ (guard built and tested in CI) |
| C7 | Background workers (Celery/beat) for reminders and email; not yet built | ☐ |

## D. Data protection and recovery

| # | Item | Status |
|---|------|--------|
| D1 | Automated encrypted backups (RPO ≤ 15 min) | ☐ |
| D2 | Restore test into an isolated environment, with ledger balances verified | ☐ |
| D3 | Disaster-recovery runbook rehearsed (`DISASTER_RECOVERY.md`) | ☐ |

## E. Security and access

| # | Item | Status |
|---|------|--------|
| E1 | Backend permission matrix and route-guard tests | ☑ CI (`test_permission_matrix.py`, `test_route_coverage.py`) |
| E2 | No self-approval; dual control on payments, bank changes and payroll | ☑ CI integration tests |
| E3 | 2FA for Director, Finance and HR/Admin | ☑ CI and e2e |
| E4 | JARVIS gateway: refusals, confirmations and audit | ☑ CI (`test_jarvis.py`) |
| E5 | Independent penetration test | ☐ |
| E6 | Dependency and image scanning in the release pipeline | ◐ (bandit and pip-audit run in CI) |

## F. Monitoring

| # | Item | Status |
|---|------|--------|
| F1 | Log shipping with request IDs | ☐ |
| F2 | Error tracking with PII scrubbing | ☐ |
| F3 | Uptime checks on `/health/live` and `/health/ready`, with alerts to the Director | ☐ |
| F4 | AI usage and cost dashboard (the data exists in `ai_usage`) | ☐ |

## G. Acceptance

| # | Item | Status |
|---|------|--------|
| G1 | User acceptance tests run by the departments (`USER_ACCEPTANCE_TESTS.md`) | ☐ |
| G2 | Devices: Windows, macOS, iPhone, Android, including the installed app | ☐ |
| G3 | Reference-image comparison per screen (`REFERENCE_IMAGE_SPECIFICATION.md`) | ◐ |
| G4 | Director sign-off to deploy | ☐ |
