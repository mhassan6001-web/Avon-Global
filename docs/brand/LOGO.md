# AVEN GLOBAL logo

- **Master artwork:** `design-references/aven-global-logo-master.png` (1536 × 1024),
  supplied by the Director on 2026-11-12. It replaces the earlier SVG emblem.
- Not a registered trademark. Registration is a separate legal step for the Director.

## Derived files (cropped from the master, never redrawn)

| File | Use |
|------|-----|
| `frontend/public/brand/aven-global-logo.jpg` | Full artwork |
| `frontend/public/brand/aven-global-lockup.jpg` | Mark, wordmark and tagline: startup screen, sign-in |
| `frontend/public/brand/aven-global-emblem.jpg` | "A" and globe: sidebar (collapsed rail shows the "A") |
| `frontend/public/brand/aven-global-wordmark.jpg` | AVEN GLOBAL lettering: sidebar |
| `frontend/public/brand/icon-{32,180,192,512}.png` | Browser, home-screen and app icons |
| `backend/app/modules/documents/assets/letterhead-banner.jpg` | PDF letterhead band (logo left, document title right) |
| `backend/app/modules/documents/assets/letterhead-banner-centred.jpg` | Word letterhead header and blank letterhead |

## Where it appears

- The app: startup screen, sign-in, sidebar, browser tab and home-screen icon.
- Every generated document: invoices, receipts, purchase orders and delivery
  notes (PDF and Word). It also appears on the blank company letterhead
  (`GET /api/v1/documents/letterhead`, Word or PDF), which every signed-in
  user can download.

## Rules

- The artwork sits on a near-black field. In the app it is blended into the
  dark interface (`mix-blend-mode: lighten`). On paper it is placed on a
  matching dark band with a champagne-gold rule.
- Do not recolour, stretch or redraw the mark. To regenerate the crops, re-run
  them from the master file.
