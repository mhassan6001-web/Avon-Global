# Deployment guide

**Do not deploy without Director approval.** Localhost is never production.
The target design is in `docs/architecture/DEPLOYMENT_ARCHITECTURE.md`.

## 1. Build

```bash
docker build -t aven-api:<sha> --target production backend
docker build -t aven-web:<sha> --target production frontend
```

Images are tagged with the commit SHA and scanned before use.

## 2. Configure (secret manager, never files)

Required in production (the API refuses to start otherwise):

- `APP_ENV=production`, `LOG_FORMAT=json`
- `DATABASE_URL` and `REDIS_URL` (non-local hosts)
- `FIELD_ENCRYPTION_KEYS` and `SIGNING_SECRET`
- `PUBLIC_BASE_URL` and `CORS_ORIGINS` (https only)

Optional, as the Director supplies them:

- `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`
- STT and TTS provider settings (the providers are not chosen yet)
- `PICOVOICE_ACCESS_KEY` and `WAKE_WORD_MODEL_URL`

The test-only providers (`fake`) are refused in production.

## 3. Release order

1. Run migrations as a one-off job: `alembic upgrade head`.
2. Roll out the API (at least 2 replicas), then the web app (at least 2
   replicas).
3. Smoke test: `/api/v1/health/ready`, sign in, Command Centre, one document
   download.
4. Watch errors for 30 minutes. Roll back by redeploying the previous tag.

## 4. Reverse proxy

- Route `/api/*` to the API and everything else to the web app.
- Allow WebSocket upgrades on `/api/v1/ws`.
- Pass `X-Forwarded-For` and `X-Forwarded-Proto`. The API runs with
  `--proxy-headers`.

## 5. First run

1. Create the Director account: `python -m app.cli create-director` (see the
   README). Check the audit chain: `python -m app.cli verify-audit-chain`.
2. Fill in the organisation profile (Admin → Organisation): legal name,
   registration number, address and currency, as recorded in
   `docs/DIRECTOR_DECISIONS.md`. Tick "Approved to print" only for confirmed
   details. Leave TPIN and VAT unticked until confirmed.
3. Finance completes setup with the accountant: accounts, periods, tax codes.
