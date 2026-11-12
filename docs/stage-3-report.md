# Stage 3 report: visual experience and sound engine

Status: **complete, verified in GitHub CI** (commit `3e04c3c` on
`stage-3-onwards`). Director instruction 2026-11-12: Stages 3–15 run
consecutively; questions are collected for one final review.

## Delivered

| Area | What was built |
|------|----------------|
| Design tokens | Grey-black surfaces (C1), two-tier gold `#B39255` / `#E6C88A` (C2), cyan only for JARVIS and live data (C3), solid gold active pill (C4), Rajdhani HUD labels (C9) and Cormorant Garamond for long reading text (C8). Fonts self-hosted. |
| Charts | Area, bar, donut, horizontal-bar, sparkline and KPI components (SVG + Framer Motion). `null` data shows a faint silhouette and "No data yet" (C5). |
| Command Centre | Recomposed after reference 08: three KPI tiles, revenue area + cash bar stack, division donut, approvals table, right rail with JARVIS, debtors, top customers and tender pipeline; platform status and all 15 stages below. |
| Sound engine | `frontend/src/lib/sound/`. Original Web Audio synthesis for 16 events. IMMERSIVE default with Balanced and Quiet presets, master / interface / notification / JARVIS-cue / JARVIS-voice volumes, seven category switches, global mute, previews. Nothing is created before the first click or key press; typing ticks are throttled to one per 90 ms and never play in password fields. |
| JARVIS visuals | Abstract particle head with gold-and-ice ribbon waveform, six states (standing by, listening, thinking, speaking, microphone off, offline). Control-chain task-flow component. Design preview on the JARVIS page, labelled; nothing listens or acts. |
| Account preferences | `auth_user_preferences` (migration 0003); `GET/PUT /api/v1/auth/preferences` with strict validation. Display and sound settings follow the user across devices. |
| Licences | `docs/legal/AUDIO_LICENCES.md`: all sounds are original procedural audio. |

## Verification (executed in CI)

| Check | Result |
|-------|--------|
| Backend tests | 127 passed (50 integration), incl. 4 new preference tests |
| mypy | no issues in 60 files |
| Alembic | downgrade base → upgrade head → check: head 0003 |
| Startup | live 200, ready 200 (database, migrations, Redis ok) |
| Frontend unit tests | 38 passed (sound engine, chart scales, JARVIS geometry, earlier suites) |
| Lint, type check, `next build` | passed |
| End-to-end (Playwright) | 10 passed: ref-08 layout shows "No data yet" (no figures), no AudioContext before a gesture, sound settings saved to the account and restored on a fresh device, JARVIS preview states and control chain |

## Not done / limits

- Side-by-side screenshot comparison with reference 08: the CI environment
  cannot return screenshots to this workspace (the Actions artifacts API is
  blocked). The composition follows ref 08 §3; the Director should review the
  Command Centre on screen. Not claimed pixel-perfect.
- JARVIS's spoken voice and wake word are Stage 12.
