# AVEN GLOBAL integration strategy

- Status: **Stage 0 deliverable, awaiting Director review.** No external
  account is assumed to be connected. Every integration is optional at
  runtime, and the system works, degraded, without it.

## 1. Principles

1. **Adapter interfaces:** each external service sits behind an interface in
   `app/platform/integrations/<kind>/`, for example `EmailSender`,
   `CalendarProvider`, `StorageBackend`, `AIProvider`,
   `SpeechToTextProvider`, `TextToSpeechProvider`, `WakeWordEngine`,
   `PushSender` and `FxRateSource`. Business modules depend only on the
   interface.
2. **Development fakes:** every interface has a development implementation
   (for example an email *outbox* page, a local storage folder, fake
   STT/TTS), so development and CI never need real accounts.
3. **Outbox and jobs:** outbound calls with side effects (sending email,
   creating calendar events) are queued from the transactional outbox. They
   use idempotency keys, retries with exponential backoff, a dead-letter
   record and a visible status. **Nothing is sent without the authorisation
   the business rule requires.**
4. **Secrets** are only in the secret manager (see DEPLOYMENT §7).
5. **Failure is visible:** integration health appears on System Status, and
   a failure never silently drops work.
6. **Data minimisation:** only the data needed is sent. AI and speech
   providers receive permission-filtered content. Voice audio is never
   stored.
7. **Terms of use:** before integrating any third-party source, its terms
   are checked and recorded. There is no scraping where terms forbid it.

## 2. Integration catalogue

| Integration | Interface | Planned provider(s) | Stage | Without it |
|-------------|-----------|---------------------|-------|------------|
| Object storage | `StorageBackend` | S3-compatible (hosting provider) | 2 / 14 | Local volume (development only) |
| Email | `EmailSender` | Provider TBD (SMTP or API) plus an authenticated sending domain (SPF, DKIM, DMARC) | 13 | Director-issued one-time links (Stage 2). In-app notifications. |
| Calendar | `CalendarProvider` | Google Workspace or Microsoft 365 (whichever the company uses), OAuth per user | 13 | In-app reminders |
| AI | `AIProvider` | **Anthropic Claude API** | 11 | JARVIS unavailable. The rest works. |
| Speech-to-text | `SpeechToTextProvider` | Shortlist in Stage 12 | 12 | Text chat |
| Text-to-speech | `TextToSpeechProvider` | Shortlist and voice auditions (CINEMATIC) in Stage 12 | 12 | Text responses |
| Wake word | `WakeWordEngine` | **Picovoice Porcupine (paid licence, AccessKey supplied by the Director later)** | 12 | Push-to-talk |
| Web push | `PushSender` | Standard Web Push (VAPID) | 15 | In-app notifications |
| SMS / WhatsApp | `MessageSender` | *Director decision whether wanted* | 13 | Not used |
| FX rates | `FxRateSource` | An official source to be chosen with the accountant (for example the central bank's published rates), with the source URL stored per rate | 7 | Manual rate entry with source and approval |
| Tender opportunities | `TenderSource` | Official procurement portals and UN/NGO procurement notices **whose terms allow automated access** (RSS/API), otherwise manual entry | 5 | Manual entry |
| Bank statements | `StatementImporter` | CSV/OFX file import per bank format | 7 | Manual reconciliation |
| Accountant export | — | Excel/CSV exports of ledgers and trial balance | 7 | — |

## 3. Inbound integrations

- **Webhooks** (email bounces, provider callbacks) are received on
  `/api/v1/integrations/<provider>/webhook`. Each call has its signature
  verified, is replay-protected, idempotent and audited.
- **No inbound integration can create financial postings directly.** They
  create drafts or records that a person reviews.

## 4. Tender monitoring rules (Stage 0 §4D, Director plan Stage 5)

- Only permitted sources are used.
- Each opportunity stores `source_url` and `source_last_checked_at`.
- Duplicates are detected by issuer, reference number and closing date.
- Opportunities are **never invented** and bids are **never submitted
  automatically**.
- Deadline alerts are calculated in the issuer's timezone and displayed in
  Africa/Blantyre time.

## 5. Failure handling summary

| Situation | Behaviour |
|-----------|-----------|
| Provider timeout or 5xx | Retry with backoff (up to 5 attempts), then dead-letter and alert |
| Authentication failure (expired OAuth or key) | Mark the integration "needs reconnect", notify the Director, stop retries |
| AI or speech outage | JARVIS reports it is unavailable. Text and manual workflows continue. |
| Storage outage | Uploads are refused with a clear message, and existing records are unaffected |
| Rate limited by the provider | Honour `Retry-After` and queue |

## 6. Testing

- Contract tests run against each adapter's fake.
- Recorded-response tests (no live calls in CI).
- A staging smoke test runs with real sandbox credentials before production.
- Failure-injection tests cover timeouts, 401, 429 and malformed payloads.
