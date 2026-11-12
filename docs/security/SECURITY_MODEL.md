# AVEN GLOBAL security model

- Status: **Model.** Stage 1 controls are implemented, as listed in
  `/SECURITY.md`. Everything else here is specified for the stage named.
- `/SECURITY.md` is the operational summary. This file is the design
  reference.

## 1. Principles

1. Enforcement happens in the backend. The UI only reflects permissions.
2. Least privilege: six initial roles plus individual grants and denies
   (Stage 2).
3. Separation of duties: no one approves their own restricted transaction.
4. Every state change is attributable to a signed-in person or to JARVIS
   acting for one, and is audit-logged.
5. Sensitive data is restricted by default: payroll, salaries, personal
   employee data, financial ledgers, and supplier bank details.

## 2. Identity (Stage 2)

- Argon2id password hashing.
- Server-side sessions in HttpOnly, Secure, SameSite=Lax cookies, delivered
  through the same-origin proxy.
- TOTP two-factor authentication. It is mandatory for Director and Finance.
- Password reset with single-use, time-limited tokens.
- Login history, plus rate limiting and lockout on authentication endpoints.
- Accounts can be suspended.

## 3. Authorisation and approvals

- Permission strings use the form `module.resource.action`, for example
  `finance.invoice.post` and `procurement.supplier_bank.change`.
- **Step-up authentication** (a fresh second factor within 5 minutes) is
  required for:
  - posting or reversing financial transactions
  - approving purchases above a threshold
  - changing supplier bank details (which also needs a second approver)
  - payroll operations
  - user and role administration

## 4. AI and voice threat model

| Threat | Control |
|--------|---------|
| A spoken command from someone nearby, a recording, or a TV | Voice is never an authenticator. Restricted actions need on-screen confirmation by the signed-in user plus step-up. The wake word only opens the microphone. |
| Prompt injection inside documents, emails or tender texts | Tool calls go through the ActionGateway regardless of model output. Approval is required for execute-category tools. External content is marked as untrusted data in prompts. |
| The model sees data the user cannot see | Results are filtered by permissions before they reach the model. Retrieval is scoped by the user. |
| Arbitrary data access | No SQL tool. Only typed service tools. |
| Unintended always-on listening | Wake-word detection is on-device, off by default, opt-in with audited consent, with a visible state and a hard stop control. No audio leaves the device before detection. |
| Audio retention | Clips are deleted after transcription. Transcripts follow the retention policy (communications policy, Stage 10). |
| JARVIS impersonating staff | Messages are labelled as JARVIS on behalf of a user. Sending as an employee is not possible. |
| Runaway cost or abuse | Per-user AI rate limits and spending caps, and a usage ledger. |

## 5. Data protection

- TLS everywhere in production. Encrypted backups (Stage 14).
- Files go to private object storage with short-lived signed URLs, behind
  permission checks (Stage 2 secure file access).
- No hidden employee surveillance. Communications retention is documented and
  visible to staff.

## 6. Security acceptance criteria (cross-stage)

`SV-01` to `SV-03` in `docs/architecture/VOICE_AND_SOUND.md`, plus the Stage 2
role-by-module access matrix tests. Every protected endpoint is tested for
every role.
